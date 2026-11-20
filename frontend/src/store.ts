import { configureStore, createSlice, PayloadAction } from "@reduxjs/toolkit";
import { UserSelf } from "./api/client";

export interface Store {
    /** 当前登录用户，未登录为 null */
    user: UserSelf | null;
    /** JWT 令牌，未登录为 null */
    token: string | null;
}

/**
 * 当前用户信息。登录成功后写入，并可用 GET /api/v1/user 刷新。
 */
export const userSlice = createSlice({
    name: "user",
    initialState: null as (UserSelf | null),
    reducers: {
        updateUserStatus(state, action: PayloadAction<UserSelf | null>) {
            return action.payload;
        },
    }
});

/**
 * JWT 令牌。同时持久化到 localStorage，刷新页面后仍然保持登录。
 */
export const tokenSlice = createSlice({
    name: "token",
    initialState: localStorage.getItem("token") as (string | null),
    reducers: {
        setToken(state: string | null, action: PayloadAction<string | null>) {
            if (action.payload != null) {
                localStorage.setItem("token", action.payload);
            } else {
                localStorage.removeItem("token");
            }
            return action.payload;
        }
    }
});

export const store = configureStore<Store>({
    reducer: {
        user: userSlice.reducer,
        token: tokenSlice.reducer,
    }
});
