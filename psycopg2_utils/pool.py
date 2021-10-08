from psycopg2.pool import AbstractConnectionPool, PoolError
from psycopg2 import extensions as _ext
import threading
import time


class ConnectionPool(AbstractConnectionPool):
    def __init__(
        self,
        idle_time: int = 2,
        *args,
        **kwargs,
    ):
        AbstractConnectionPool.__init__(self, *args, **kwargs)
        # Construct Semaphore with maxconn. This will enable restricting
        # the number of connections that are being used to not exceed the
        # number of connections which causes the psycopg2 pool to raise an
        # exception
        self._connectionLock = threading.Semaphore(int(self.maxconn))
        self._idle_pool = []
        self._last_used = {}  # id(conn): time
        self._in_use_connections = {}  # id(conn): conn
        self._lock = threading.Lock()
        # The daemon will run periodically and call putconn for all connections
        # that haven't been used for some amount of time
        self.daemon = threading.Thread(
            target=self.trim_pool, args=(idle_time,), daemon=True
        )
        self.daemon.start()

    def trim_pool(self, number_of_sec: int):
        while True and not self.closed:
            # Yield the cpu to other threads for `number_of_sec` sec.
            # This is the least overhead but a connection might live for almost
            # 2 * number_of_sec sec
            time.sleep(number_of_sec)
            if self.closed:
                # Stops the deamon if the pool has been closed
                break

            with self._lock:
                # This only closes connections that have been idle for
                # `number_of_sec` sec
                t = time.time() - number_of_sec
                keep_conn = []
                close_conn = []
                for conn in self._idle_pool:
                    if self._last_used[id(conn)] > t:
                        keep_conn.append(conn)
                    else:
                        close_conn.append(conn)

                for conn in close_conn:
                    del self._last_used[id(conn)]
                    self._putconn(conn)

                self._idle_pool = keep_conn

    def getconn(self):
        if self.closed:
            raise PoolError("connection pool is closed")
        self._connectionLock.acquire()
        with self._lock:
            if self._idle_pool:
                # Get the oldest conn in the pool
                conn = self._idle_pool.pop(0)
            else:
                # If there is no connection in the pool then we open a new
                # connection
                conn = self._getconn()

            self._in_use_connections[id(conn)] = conn

            return conn

    def putconn(self, conn):
        try:
            if self.closed:
                raise PoolError("connection pool is closed")
            with self._lock:
                # We need to handle all the clean up for the connection
                key = id(conn)
                if not conn.closed:

                    status = conn.info.transaction_status
                    if status == _ext.TRANSACTION_STATUS_UNKNOWN:
                        # server connection lost
                        conn.close()
                    else:
                        if status != _ext.TRANSACTION_STATUS_IDLE:
                            # connection in error or in transaction
                            conn.rollback()
                        self._last_used[key] = time.time()
                        self._idle_pool.append(conn)

                if not self.closed and key in self._in_use_connections:
                    del self._in_use_connections[key]
        finally:
            self._connectionLock.release()

    def closeall(self):
        with self._lock:
            self._closeall()
