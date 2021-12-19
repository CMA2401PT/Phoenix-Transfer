// 对 fb 的main函数做以下修改：
// 注意：本项目仅仅实现对fb的开孔，不属于本项目范畴的任务，例如
// 解决编译完成后的 版本无效 问题，本项目不会给出任何说明，请自行解决
// fb 版本 v0.5.1

// 修改 import
import (
	"C"
	"bufio"
	"bytes"
	"encoding/binary"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"net"
	"os"
	"path/filepath"
	"phoenixbuilder/fastbuilder/command"
	"phoenixbuilder/fastbuilder/configuration"
	fbauth "phoenixbuilder/fastbuilder/cv4/auth"
	"phoenixbuilder/fastbuilder/function"
	I18n "phoenixbuilder/fastbuilder/i18n"
	"phoenixbuilder/fastbuilder/menu"
	"phoenixbuilder/fastbuilder/plugin"
	"phoenixbuilder/fastbuilder/signalhandler"
	fbtask "phoenixbuilder/fastbuilder/task"
	"phoenixbuilder/fastbuilder/types"
	"phoenixbuilder/minecraft"
	"phoenixbuilder/minecraft/protocol/packet"
	"phoenixbuilder/minecraft/utils"
	"runtime"
	"runtime/debug"
	"strings"
	"syscall"
	"time"

	"github.com/google/uuid"
	"github.com/pterm/pterm"
	"golang.org/x/term"
)

// 添加一个开孔函数
// 计划下一个版本将这里作为 tcp server 端，而不是 clinet 端
func forward(conn *minecraft.Conn) func(data []byte, err error) error {
	reader := bufio.NewReader(os.Stdin)
	fmt.Printf("target address (Default: localhost:8000):")
	input, _ := reader.ReadString('\n')
	forwardAddress := strings.TrimRight(input, "\r\n")
	if forwardAddress == "" {
		forwardAddress = "localhost:8000"
	}
	// forwardAddress := "localhost:8000"
	forawrdDialer := net.Dialer{Timeout: time.Second * 10}
	proxy, err := forawrdDialer.Dial("tcp", forwardAddress)
	if err != nil {
		fmt.Printf("try forward -> %s failed\n", forwardAddress)
		return nil
	}
	fmt.Printf("forward: fb -> proxy %s successfully\n", forwardAddress)
	// choker.Lock()
	forwardFlag := true
	closeFun := func() {
		fmt.Printf("forward closed\n")
		forwardFlag = false
		// choker.Unlock()
		proxy.Close()
	}

	// forward read
	forwardRead := func(data []byte, err error) error {
		if !(err == nil && forwardFlag) {
			closeFun()
			return fmt.Errorf("forward closed")
		}
		dataLen := len(data) + 4
		headerBytes := make([]byte, 4)
		binary.LittleEndian.PutUint32(headerBytes, uint32(dataLen))
		markedPacketBytes := append(headerBytes, data...)
		currentBytes := 0
		for currentBytes != dataLen {
			writedBytes, err := proxy.Write(markedPacketBytes[currentBytes:dataLen])
			if err != nil {
				closeFun()
				return fmt.Errorf("forward closed %v", err)
			}
			currentBytes += writedBytes
		}
		// fmt.Printf("forward fb -> proxy %v\n", data)
		return nil
	}
	// forward send
	go func() {
		buf := make([]byte, 0)
		currentBytes := 0
		requiredBytes := 0
		for forwardFlag {
			if requiredBytes == 0 {
				rbuf := make([]byte, 4-currentBytes)
				nbytes, err := proxy.Read(rbuf)
				// fmt.Printf("read %d", nbytes)
				if err != nil || nbytes == 0 {
					closeFun()
					return
				}
				currentBytes += nbytes
				buf = append(buf, rbuf...)
				if currentBytes >= 4 {
					requiredBytes = int(binary.LittleEndian.Uint32(buf[:4]))
				}
			}
			if currentBytes < requiredBytes {
				rbuf := make([]byte, requiredBytes-currentBytes)
				nbytes, err := proxy.Read(rbuf)
				// fmt.Printf("read %d", nbytes)
				if err != nil || nbytes == 0 {
					closeFun()
					return
				}
				currentBytes += nbytes
				buf = append(buf, rbuf...)
			}
			if currentBytes >= requiredBytes {
				if conn.WritePacketBytes(buf[4:requiredBytes]) != nil {
					closeFun()
					return
				}
				fmt.Printf("forward fb <- proxy %v\n", buf[4:requiredBytes])
				buf = buf[requiredBytes:currentBytes]
				currentBytes -= requiredBytes
				requiredBytes = 0
			}
		}
	}()
	return forwardRead
}

// 原函数第 244行，添加一个函数变量
// zeroId, _ := uuid.NewUUID()
// oneId, _ := uuid.NewUUID()
// configuration.ZeroId = zeroId
// configuration.OneId = oneId
// types.ForwardedBrokSender = fbtask.BrokSender <-244 行
var forwardRecvFunc func(data []byte, err error) error

// 原函数 281行，添加一个选项：
//if cmd[0] == '>'&&len(cmd)>1 {
// 	umsg:=cmd[1:]
// 	if(!client.CanSendMessage()) {
// 		command.WorldChatTellraw(conn, "FastBuildeｒ", "Lost connection to the authentication server.")
// 		break
// 	}
// 	client.WorldChat(umsg)
// } <-281 行
if cmd == "forward" {
	forwardRecvFunc = forward(conn)
}

// 修改原函数 289行，处理逻辑
// pk, err := conn.ReadPacket() <- 289 行
pk, data, err := conn.ReadPacketAndBytes()
if forwardRecvFunc != nil {
	forwardErr := forwardRecvFunc(data, err)
	if forwardErr != nil {
		forwardRecvFunc = nil
	}
}