import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Redirect, Route, RouteProps, Switch, useLocation } from "react-router-dom";
import { Store, userSlice } from "./store";
import { fetchUser, isAuthenticated } from "./api/client";
import { Routes } from "./api/urls";
import { roleHome } from "./roles";
import { LoginPage } from "./pages/LoginPage";
import { ExamListPage } from "./pages/student/ExamListPage";
import { PrecheckPage } from "./pages/student/PrecheckPage";
import { WorkbenchPage } from "./pages/student/WorkbenchPage";
import { ResultPage } from "./pages/student/ResultPage";
import { ReportPage } from "./pages/student/ReportPage";
import { ExamManagePage } from "./pages/teacher/ExamManagePage";
import { ExamCreatePage } from "./pages/teacher/ExamCreatePage";
import { ProblemConfigPage } from "./pages/teacher/ProblemConfigPage";
import { ProctorPage } from "./pages/teacher/ProctorPage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { ToastHost } from "./components/Toast";
import { isDemo, loadDemoUser } from "./demo";

/**
 * 登录校验：没有令牌跳登录页；有令牌但用户信息还没拉到时先渲染一个空壳，
 * 由 App 统一在启动时请求 GET /api/v1/user 填充。
 */
function RequireAuth({ children }: { children: React.ReactNode }) {
    const location = useLocation();
    if (!isAuthenticated()) {
        return <Redirect to={{ pathname: Routes.login, state: { from: location.pathname } }}/>;
    }
    return <>{children}</>;
}

/** 根路径：按角色跳到对应首页 */
function HomeRedirect() {
    const user = useSelector((s: Store) => s.user);
    if (!isAuthenticated()) {
        return <Redirect to={Routes.login}/>;
    }
    if (!user) {
        return <div className="student-page"/>;
    }
    return <Redirect to={roleHome(user.role)}/>;
}

export function App() {
    const token = useSelector((s: Store) => s.token);
    const user = useSelector((s: Store) => s.user);
    const dispatch = useDispatch();
    const [booting, setBooting] = useState(!!token && !user);

    // 刷新页面后，用本地令牌换回当前用户信息；演示模式直接读本地演示用户
    useEffect(() => {
        let alive = true;
        if (token && !user && isDemo()) {
            const demoUser = loadDemoUser();
            if (demoUser) {
                dispatch(userSlice.actions.updateUserStatus(demoUser));
            }
            setBooting(false);
        } else if (token && !user) {
            setBooting(true);
            fetchUser()
                .then(result => {
                    if (!alive) {
                        return;
                    }
                    if (result.success) {
                        dispatch(userSlice.actions.updateUserStatus(result.user));
                    }
                    setBooting(false);
                })
                .catch(() => {
                    // 后端没起来时不阻塞界面，交由各页面自身的空状态处理
                    if (alive) {
                        setBooting(false);
                    }
                });
        } else {
            setBooting(false);
        }
        return () => {
            alive = false;
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [token]);

    if (booting) {
        return <div className="student-page"/>;
    }

    return (
        <>
        <ToastHost/>
        <Switch>
            <Route exact path={Routes.login} component={LoginPage}/>
            <Route exact path="/" component={HomeRedirect}/>

            <Route exact path={Routes.examList}
                   render={() => <RequireAuth><ExamListPage/></RequireAuth>}/>
            <Route exact path="/exams/:examId/precheck"
                   render={() => <RequireAuth><PrecheckPage/></RequireAuth>}/>
            <Route exact path="/exams/:examId/workbench"
                   render={() => <RequireAuth><WorkbenchPage/></RequireAuth>}/>
            <Route exact path="/exams/:examId/result"
                   render={() => <RequireAuth><ResultPage/></RequireAuth>}/>
            <Route exact path="/exams/:examId/report"
                   render={() => <RequireAuth><ReportPage/></RequireAuth>}/>

            <Route exact path={Routes.examManage}
                   render={() => <RequireAuth><ExamManagePage/></RequireAuth>}/>
            <Route exact path={Routes.examCreate}
                   render={() => <RequireAuth><ExamCreatePage/></RequireAuth>}/>
            <Route exact path="/manage/:examId/problems"
                   render={() => <RequireAuth><ProblemConfigPage/></RequireAuth>}/>
            <Route exact path="/manage/:examId/proctor"
                   render={() => <RequireAuth><ProctorPage/></RequireAuth>}/>

            <Route component={NotFoundPage as React.ComponentType<RouteProps>}/>
        </Switch>
        </>
    );
}
