// 在 fb 对应文件中添加以下两个函数

func (conn *Conn) WritePacketBytes(data []byte) error {
	conn.sendMutex.Lock()
	defer conn.sendMutex.Unlock()

	conn.bufferedSend = append(conn.bufferedSend, append([]byte(nil), data...))
	conn.writeBuf.Reset()
	return nil
}

// func (conn *Conn) ReadPacketBytes() (data []byte, err error) {
// 	if data, ok := conn.takePushedBackPacket(); ok {
// 		return data, nil
// 	}

// 	select {
// 	case data := <-conn.packets:
// 		return data, nil
// 	case <-conn.readDeadline:
// 		return nil, fmt.Errorf("error reading packet: read timeout")
// 	case <-conn.closeCtx.Done():
// 		return nil, fmt.Errorf("error reading packet: connection closed")
// 	}
// }

func (conn *Conn) ReadPacketAndBytes() (k packet.Packet, data []byte, err error) {
	if data, ok := conn.takePushedBackPacket(); ok {
		pk, err := conn.parsePacket(data, false)
		if err != nil {
			conn.log.Println(err)
			return conn.ReadPacketAndBytes()
		}
		return pk, data, nil
	}

	select {
	case data := <-conn.packets:
		pk, err := conn.parsePacket(data, true)
		if err != nil {
			conn.log.Println(err)
			return conn.ReadPacketAndBytes()
		}
		return pk, data, nil
	case <-conn.readDeadline:
		return nil, nil, fmt.Errorf("error reading packet: read timeout")
	case <-conn.closeCtx.Done():
		return nil, nil, fmt.Errorf("error reading packet: connection closed")
	}
}