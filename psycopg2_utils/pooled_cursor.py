from functools import wraps
from .Cursor import Cursor


def pooled_cursor(m):
    """
    Decorator that assumes that wrapped method accepts cursor as parameter.
    If there is `DictCursor` in the method request then this
    function gets a connection from connection pool. It creates a new cursor, delegates
    to the method, then commits, closes the cursors and return connection to pool.

    If a parameter of the method is a `DictCursor` this wrapper does nothing
    and expects the calling method to handle commiting, and closing the cursor,
    and returning the connection to the pool.
    :param method to decorate with pooled cursor
    :return:
    """

    @wraps(m)
    def wrapper(self, *args, **kwargs):
        con = None
        cur = None
        result = None
        # Check if there is a DictCursor in the arguments
        if any([isinstance(a, Cursor) for a in args]) or "cursor" in kwargs:
            return m(self, *args, **kwargs)
        try:
            retry_count = 0
            while 1:
                try:
                    con = self.pool.getconn()
                    cur = con.cursor(cursor_factory=Cursor)
                    result = m(self, *args, cursor=cur, **kwargs)
                except Exception as e:
                    if retry_count == 3:
                        raise e
                    retry_count += 1
                    if con:
                        self.pool.putconn(con)
                    continue
                break
            if con:
                con.commit()
            if cur:
                cur.close()
        finally:
            if con:
                self.pool.putconn(con)
        return result

    return wrapper
