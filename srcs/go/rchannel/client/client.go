package client

import (
	"time"

	"github.com/lsds/KungFu/srcs/go/monitor"
	"github.com/lsds/KungFu/srcs/go/plan"
	"github.com/lsds/KungFu/srcs/go/rchannel/connection"
)

type Client struct {
	self     plan.PeerID
	connPool *ConnectionPool
	monitor  monitor.Monitor
}

func New(self plan.PeerID) *Client {
	return &Client{
		self:     self,
		connPool: newConnectionPool(),
		monitor:  monitor.GetMonitor(),
	}
}

func (c *Client) Ping(target plan.PeerID) (time.Duration, error) {
	t0 := time.Now()
	conn, err := connection.NewPingConnection(target, c.self)
	if err != nil {
		return time.Since(t0), err
	}
	defer conn.Close()
	var empty connection.Message
	if err := conn.Send("ping", empty, connection.NoFlag); err != nil {
		return time.Since(t0), err
	}
	if err := conn.Read("ping", empty); err != nil {
		return time.Since(t0), err
	}
	return time.Since(t0), nil
}

// Send sends data in buf to given Addr
func (c *Client) Send(a plan.Addr, buf []byte, t connection.ConnType, flags uint32) error {
	msg := connection.Message{
		Length: uint32(len(buf)),
		Data:   buf,
	}
	if err := c.send(a, msg, t, flags); err != nil {
		return err
	}
	c.monitor.Egress(int64(msg.Length), a.NetAddr())
	return nil
}

func (c *Client) send(a plan.Addr, msg connection.Message, t connection.ConnType, flags uint32) error {
	conn := c.connPool.get(a.Peer(), c.self, t)
	if err := conn.Send(a.Name, msg, flags); err != nil {
		return err
	}
	return nil
}

func (c *Client) ResetConnections(keeps plan.PeerList, token uint32) {
	c.connPool.reset(keeps, token)
}
