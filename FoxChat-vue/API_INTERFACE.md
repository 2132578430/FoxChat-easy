# API 接口文档 (API Interfaces)

本项目为纯前端项目，目前使用 `Mock.js` 模拟后端接口。以下是前端期望的后端接口定义。

所有请求的基础路径 (Base URL): `/api`

## 1. 用户认证模块 (Auth)

### 1.1 用户登录 (Login)
*   **URL**: `/auth/login`
*   **Method**: `POST`
*   **Content-Type**: `application/json`
*   **Request Body**:
    ```json
    {
      "username": "admin",  // 用户名
      "password": "123"     // 密码
    }
    ```
*   **Response (Success)**:
    ```json
    {
      "code": 200,
      "msg": "登录成功",
      "data": {
        "userInfo": {
          "token": "eyJhbGciOiJIUzI1Ni...",
          "id": "user_001",
          "username": "admin",
          "face_image": "https://..."
        }
      }
    }
    ```

### 1.2 用户注册 (Register)
*   **URL**: `/auth/register`
*   **Method**: `POST`
*   **Content-Type**: `application/json`
*   **Request Body**:
    ```json
    {
      "nickname": "测试用户",
      "username": "testuser",
      "password": "password123",
      "email": "test@example.com",
      "code": "123456"
    }
    ```
*   **Response (Success)**:
    ```json
    {
      "code": 1000,
      "msg": "注册成功",
      "data": {}
    }
    ```
*   **Response (Error)**:
    ```json
    {
      "code": 12000,
      "msg": "账号或密码格式错误",
      "data": {}
    }
    ```
    ```json
    {
      "code": 12001,
      "msg": "验证码错误",
      "data": {}
    }
    ```

### 1.3 发送验证码 (Send Code)
*   **URL**: `/auth/sendCode`
*   **Method**: `POST`
*   **Content-Type**: `application/json`
*   **Request Body**:
    ```json
    {
      "email": "test@example.com"
    }
    ```
*   **Response (Success)**:
    ```json
    {
      "code": 1000,
      "msg": "验证码发送成功",
      "data": {}
    }
    ```

## 2. 模拟数据说明 (Mock Data)

*   **Mock文件位置**: `src/mock/index.js`
*   **默认测试账号**:
    *   用户名: `admin`
    *   密码: `123456`
