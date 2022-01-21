// 在 fb 对应文件(minecraft/conn.go)中添加以下两个函数

func (conn *Conn) WritePacketBytes(data []byte) error {
	select {
	case <-conn.close:
		return conn.closeErr("write packet")
	default:
	}
	conn.sendMu.Lock()
	defer conn.sendMu.Unlock()

	conn.bufferedSend = append(conn.bufferedSend, append([]byte(nil), data...))
	return nil
}

func (conn *Conn) ReadPacketAndBytes() (pk packet.Packet, data []byte, err error) {
	if data, ok := conn.takeDeferredPacket(); ok {
		pk, err := data.decode(conn)
		if err != nil {
			conn.log.Println(err)
			return conn.ReadPacketAndBytes()
		}
		return pk, data.full, nil
	}

	select {
	case <-conn.close:
		return nil, nil, conn.closeErr("read packet")
	case <-conn.readDeadline:
		return nil, nil, conn.wrap(context.DeadlineExceeded, "read packet")
	case data := <-conn.packets:
		pk, err := data.decode(conn)
		if err != nil {
			conn.log.Println(err)
			return conn.ReadPacketAndBytes()
		}
		return pk, data.full, nil
	}
}