# psycopg2 utils

This package contains helper classes for psycopg2.

## Installation
```bash
pip install psycopg2-utils
```

## ConnectionPool
This connection pool is thread safe and does not raise an exception when the pool is
empty and a thread tried to get a connection from it. Instead the thread will wait
for a connection to become available in the pool.
Connections will also not be closed when returned to the pool until they have been
idle for some specified time.

```python
from psycopg2_utils import ConnectionPool

config = {
    "minconn": os.environ["DB_MINCONN"],
    "maxconn": os.environ["DB_MAXCONN"],
    "idle_time": os.environ["IDLE_TIME"],
    "dbname": os.environ["DB_NAME"],
    "host": os.environ["DB_HOST"],
    "port": os.environ["DB_PORT"],
    "user": os.environ["DB_USER"],
    "password": os.environ["DB_PASS"],
    "options": "-c search_path={}".format(os.environ["DB_SCHEMA"]),
}
pool = ConnectionPool(**config)

# Get connection from the pool
con = pool.getconn()

# Return connection to the pool
pool.putconn(con)
```

## Cursor
This cursor extends the dict curser and enables logging the sql queries when the log
level is set to DEBUG and also logs how long each query takes to execute if log level
is INFO and there is an environment variable named METRIC_LOGGING that has the value
"TRUE".

```python
from psycopg2 import connect
from psycopg2_utils import Cursor

con = connect("")
cur = con.cursor(cursor_factory=Cursor)
```

## pooled_cursor
This allows a method of a class to be decorated so that it will automatically supply
the method with a cursor to use.
It requires that the class has a property named pool containing a connection pool that
implements the `AbstractConnectionPool`.

```python
from psycopg2_utils import pooled_cursor

class MyClass:
    def __init__(self, config):
        self.pool = ConnectionPool(**config)

    @pooled_cursor
    def get_count(self, cursor):
        cursor.execute("SELECT count(*) FROM table;")
        return cursor.fetchone()[0]

my_class = MyClass(config)

#The method can then be used like this:
count = my_class.get_count()

# If you already hold a cursor and don't want to get a new one
# from the pool then it can be passed into the method.
cursor = some_method_that_gets_cursor()
count = my_class.get_count(cursor=cursor)
```

The wrapper will take care of getting a connection from the pool and returning it to
the pool at the end. It also does a commit when there is no exception.

