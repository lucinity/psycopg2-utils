import psycopg2
import psycopg2.extras
import logging
import time
import os

log_metrics = os.environ.get("METRIC_LOGGING", "FALSE").upper() == "TRUE"


class Cursor(psycopg2.extras.DictCursor):
    """
    Cursor that adds debug and metric logging.

    - If LogLevel is at least DEBUG, then the sql query that is about to be executed
    will be logged
    - If LogLevel is at least INFO and METRIC_LOGGING is TRUE, then the query action,
    table name, and execution time will be logged.
    """

    def execute(self, sql, args=None):
        logger = logging.getLogger(__name__)
        if logger.isEnabledFor(logging.DEBUG):
            # mogrify constructs the sql query that would be sent to the backend
            logger.debug(self.mogrify(sql, args))

        try:
            if logger.isEnabledFor(logging.INFO) and log_metrics:
                t = time.time()

            super().execute(sql, args)

            if logger.isEnabledFor(logging.INFO) and log_metrics and t:
                # Sometimes `sql` is bytes rather than string.
                sql_str = str(sql, "utf-8") if isinstance(sql, bytes) else sql
                # Remove all extra spaces and new line chars
                sql_ = " ".join(sql_str.strip().split()).split()
                if sql_:
                    action = sql_[0].upper()
                    if action == "UPDATE":
                        # UPDATE cases SET ...
                        # For update the table name is the second value in the list
                        table_name = sql_[1]
                    elif action == "INSERT" or action == "DELETE":
                        # INSERT INTO cases ...
                        # DELETE FROM cases ...
                        # For insert and delete the table name is the third value in the
                        # list
                        table_name = sql_[2]
                    elif action == "SELECT":
                        # For select the table name is the value that comes after FROM
                        table_name = sql_[sql_.index("FROM") + 1]
                    else:
                        # We have some queries that start with `WITH ...`, we need to
                        # map those
                        table_name = "UNKNOWN"
                    logger.info(
                        f"ACTION={action} | TABLE={table_name} | TIME={time.time() - t}"
                    )
        except Exception as exc:
            logger.exception("%s: %s" % (exc.__class__.__name__, exc))
            raise
