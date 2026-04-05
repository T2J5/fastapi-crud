## 参数

### 路径参数

/book/{book_id}
路径参数出现在URL中，使用 Path 进行注解

### 查询参数

声明的参数不是路径参数时，路径操作函数会把参数自动解释为查询参数
使用Query进行参数注解

### 请求体参数

Field进行参数注解

## 响应格式

response_class

FileResponse HtmlResponse

## 自定义响应数据格式

response_model

## 错误处理

HTTPException

## 中间件

@app.middleware("http") 自下向上执行
async def middleware(req, call_next):

## 依赖注入

Depends(common_params)

## ORM
sqlalchemy aiomysql

create_async_engine
