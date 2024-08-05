from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
# 데이터베이스 접속
DATABASE_URL = "mysql+pymysql://funcoding:funcoding@localhost/my_memo_app"
# 데이터베이스 접속 선언
engine = create_engine(DATABASE_URL)
# 세션관련된 선언
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
# 데이터베이스 선언
Base = declarative_base()
'''
def get_db():
    db = Session(bind=engine)
    try:
        yield db
    finally:
        db.close()
'''