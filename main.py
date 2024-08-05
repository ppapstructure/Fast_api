# 02 관련
# Jinja template좀 복습해봐야 겠다
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, declarative_base
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, ForeignKey
#from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel
from typing import Optional
from passlib.context import CryptContext
from starlette.middleware.sessions import SessionMiddleware

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="your-secret-key")
templates = Jinja2Templates(directory="templates")

DATABASE_URL = "mysql+pymysql://funcoding:funcoding@localhost/my_memo_app"
engine = create_engine(DATABASE_URL)
Base = declarative_base()

# 회원목록
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True)
    email = Column(String(200))
    hashed_password = Column(String(512))

# 회원가입시 데이터 검증
class UserCreate(BaseModel):
    username : str
    email : str
    password : str # 해시전 패스워드를 받습니다

# 회원로그인시 데이터 검증
class UserLogin(BaseModel):
    username : str
    password : str # 해시전 패스워드를 받습니다.

# 메모
class Memo(Base):
    __tablename__ = 'memo'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    title = Column(String(100))
    content = Column(String(1000))

class MemoCreate(BaseModel):
    title : str
    content : str

class MemoUpdate(BaseModel):
    title : Optional[str] = None
    content : Optional[str] = None

def get_db():
    db = Session(bind=engine)
    try:
        yield db
    finally:
        db.close()

Base.metadata.create_all(bind=engine)

# 회원 가입
@app.post("/signup")
async def signup(signup_data: UserCreate, db: Session = Depends(get_db)):
    # 먼저 username이 이미 존재하는지 확인
    existing_user = db.query(User).filter(User.username == signup_data.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="이미 동일 사용자 이름이 가입되어 있습니다.")

    hashed_password = get_password_hash(signup_data.password)
    new_user = User(username=signup_data.username, email=signup_data.email, hashed_password=hashed_password)
    db.add(new_user)

    try:
        db.commit()
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="회원가입이 실패했습니다. 기입한 내용을 확인해보세요.")

    db.refresh(new_user)
    return {"message":"회원가입을 성공했습니다."}

# 로그인
@app.post("/login")
async def login(request: Request, signin_data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == signin_data.username).first()
    if user and verify_password(signin_data.password, user.hashed_password):
        request.session["username"] = user.username
        return {"message": "로그인이 성공했습니다."}
    else:
        raise HTTPException(status_code=401, detail="Invalid credentials")

# 로그아웃
@app.post("/logout")
async def logout(request: Request):
    request.session.pop("username", None)
    return {"message":"로그아웃이 성공했습니다."}

# 메모 생성
@app.post("/memos/")
async def create_memo(request: Request, memo: MemoCreate, db: Session = Depends(get_db)):
    username = request.session.get("username")
    if username is None:
        raise HTTPException(status_code=401, detail="Not authorized")
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    new_memo = Memo(user_id=user.id, title=memo.title, content=memo.content)
    db.add(new_memo)
    db.commit()
    db.refresh(new_memo)
    return new_memo

# 메모 조회
@app.get("/memos/")
async def list_memos(request: Request, db: Session = Depends(get_db)):
    username = request.session.get("username")
    if username is None:
        raise HTTPException(status_code=401, detail="Not authorized")
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    memos = db.query(Memo).filter(Memo.user_id == user.id).all() # memos에 list 형태로 반환
    #return {"memos": memos, "username":username}
    return templates.TemplateResponse("memos.html",{"request": request, "memos":memos, "username":username})

# 메모 수정
@app.put("/memos/{memo_id}")
async def update_memo(request: Request, memo_id: int, memo: MemoUpdate, db: Session = Depends(get_db)):
    username = request.session.get("username")
    if username is None:
        raise HTTPException(status_code=401, detail="Not authorized")
    user = db.query(User).filter(User.username == username).first()

    if user is None:
        raise HTTPException(status_code = 404, detail="User not found")
    
    db_memo = db.query(Memo).filter(Memo.user_id == user.id, Memo.id == memo_id).first()

    if memo.title is not None:
        db_memo.title = memo.title
    if memo.content is not None:
        db_memo.content = memo.content 

    db.commit()
    db.refresh(db_memo)
    return db_memo

# 메모 삭제
@app.delete("/memos/{memo_id}")
async def delete_memo(request: Request ,memo_id: int, db: Session = Depends(get_db)):
    username = request.session.get("username")
    if username is None:
        raise HTTPException(status_code=401, detail="Not authorized")
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(status_code = 404, detail="User not found")
    
    db_memo = db.query(Memo).filter(Memo.user_id == user.id ,Memo.id == memo_id).first()
    if db_memo is None:
        return ({"error": "Memo not found"})
    
    db.delete(db_memo)
    db.commit()
    return ({"message": "Memo deleted"})

# 기존 라우트
@app.get('/')
async def read_root(request: Request):
    return templates.TemplateResponse('home.html', {"request": request})

@app.get("/about")
async def about():
    return {"message": "이것은 마이 메모 앱의 소개 페이지 입니다."}

### 1차

'''
1. 메모(생성, 조회, 수정, 삭제)
'''
### 2차

'''
1. 로그인 후 접속이 가능한 페이지(SessionMiddleware)
2. 회원가입시 등록한 패스워드를 어떻게 저장할 것인지
    - plain text를 hashing기법을 사용해서, 알아볼 수 없는 데이터로 저장
    - 패스워드 입력시, 동일 hashing기법으로 변환한 후, 데이터베이스의 데이터로 확인

세션미들웨어 정의, 패스워드 라이브러리 설정
'''