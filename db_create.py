from sqlalchemy import Table, Column, Integer, String, MetaData, create_engine

engine = create_engine('sqlite:///db.sqlite3', echo = True)
meta = MetaData()

user = Table(
    'user', meta,
    Column('id', Integer, primary_key=True),
    Column('name', String(100)),
    Column('email', String(70), unique=True),
    Column('password', String(100))
)

meta.create_all(engine)