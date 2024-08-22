from common import db
import sqlalchemy as sqla


class Querier:
    engine: sqla.Engine

    def __init__(self):
        self.engine = db._ENGINE
