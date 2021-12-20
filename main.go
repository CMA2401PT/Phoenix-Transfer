// 对 fb 的main函数做以下修改：
// 注意：本项目仅仅实现对fb的开孔，不属于本项目范畴的任务，例如
// 解决编译完成后的 版本无效 问题，本项目不会给出任何说明，请自行解决
// fb 版本 v0.5.1


// 添加开孔函数
// FB 为 server端，工作在 localhost:8000端口
func forwardSend(srcConn net.Conn, dstConn *minecraft.Conn) {
	buf := make([]byte, 0)
	currentBytes := 0
	requiredBytes := 0
	for {
		if requiredBytes == 0 {
			rbuf := make([]byte, 4-currentBytes)
			nbytes, err := srcConn.Read(rbuf)
			if err != nil || nbytes == 0 {
				srcConn.Close()
				fmt.Printf("Transfer: connection (proxy -> fb) closed, because cannot read first 4 bytes from proxy\n\t(err=%v)\n", err)
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
			nbytes, err := srcConn.Read(rbuf)
			if err != nil || nbytes == 0 {
				srcConn.Close()
				fmt.Printf("Transfer: connection (proxy -> fb) closed, because cannot correctly read from proxy\n\t(err=%v)\n", err)
				return
			}
			currentBytes += nbytes
			buf = append(buf, rbuf...)
		}
		if currentBytes >= requiredBytes {
			if dstConn.WritePacketBytes(buf[4:requiredBytes]) != nil {
				srcConn.Close()
				fmt.Print("Transfer: connection (proxy -> fb) closed, because fb -> mc forward fail\n")
				return
			}
			// fmt.Printf("forward fb <- proxy %v\n", buf[4:requiredBytes])
			buf = buf[requiredBytes:currentBytes]
			currentBytes -= requiredBytes
			requiredBytes = 0
		}
	}
}

func StartTransferServer(conn *minecraft.Conn, transferPort string) func(data []byte) {
	listener, err := net.Listen("tcp", transferPort)
	if err != nil {
		fmt.Printf("Transfer: listen fail\n\t(err=%v)\n", err)
		return nil
	}
	fmt.Println("Transfer: server start successfully @ ", transferPort)
	proxyConnMap := make(map[string]net.Conn)

	// 使用一个协程等待连接
	go func() {
		for {
			proxyConn, err := listener.Accept()
			if err != nil {
				fmt.Printf("Transfer: accept new connection fail\n\t(err=%v)\n", err)
				continue
			}
			fmt.Printf("Transfer: accept new connection @ %v\n", proxyConn.RemoteAddr().String())
			proxyConnMap[proxyConn.RemoteAddr().String()] = proxyConn
			// 对于每个连接 使用一个协程处理 proxy -> fb -> mc 转发
			go forwardSend(proxyConn, conn)
		}
	}()

	// 定义单次的 mc -> fb -> proxy 转发函数
	forwardRead := func(data []byte) {
		dataLen := len(data) + 4
		headerBytes := make([]byte, 4)
		binary.LittleEndian.PutUint32(headerBytes, uint32(dataLen))
		markedPacketBytes := append(headerBytes, data...)
		for addr := range proxyConnMap {
			proxyConn := proxyConnMap[addr]
			currentBytes := 0
			for currentBytes != dataLen {
				writedBytes, err := proxyConn.Write(markedPacketBytes[currentBytes:dataLen])
				if err != nil || writedBytes == 0 {
					fmt.Printf("Transfer: connection (fb -> proxy) closed, because cannot correctly write to proxy\n\t(err=%v)\n", err)
					delete(proxyConnMap, addr)
					break
				}
				currentBytes += writedBytes
			}
		}
	}
	return forwardRead
}

// 原函数第 284行后，添加一行代码启动 Transfer Server
//     } <-283
// } ()  <-284
forwardRecvFunc := StartTransferServer(conn, "localhost:8000") // <-插入在284行后

// 原函数 289 ～ 293 行，修改逻辑
// pk, err := conn.ReadPacket() <-289
// if err != nil { <-290
//     panic(err) <-291
// } <-292
//  <-293
// 修改为
pk, data, err := conn.ReadPacketAndBytes()
if err != nil {
	panic(err)
}
if forwardRecvFunc != nil {
	forwardRecvFunc(data)
}