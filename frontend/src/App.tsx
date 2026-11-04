import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Redirect, Route, RouteProps, Switch, useLocation } from "react-router-dom";
import { Store, userSlice } from "./store";
import { fetchUser, isAuthenticated } from "./api/client";
import { Routes } from "./api/urls";
import { Role, roleHome } from "./roles";
import { LoginPage } from "./pages/LoginPage";
import { RegisterPage } from "./pages/RegisterPage";
import { ExamListPage } from "./pages/student/ExamListPage";
import { PrecheckPage } from "./pages/student/PrecheckPage";
import { WorkbenchPage } from "./pages/student/WorkbenchPage";
import { ResultPage } from "./pages/student/ResultPage";
import { ReportPage } from "./pages/student/ReportPage";
import { ExamManagePage } from "./pages/teacher/ExamManagePage";
import { ExamCreatePage } from "./pages/teacher/ExamCreatePage";
import { ProblemConfigPage } from "./pages/teacher/ProblemConfigPage";
import { ProctorPage } from "./pages/teacher/ProctorPage";
import { ProblemBankPage } from "./pages/teacher/ProblemBankPage";
import { AccountsPage } from "./pages/teacher/AccountsPage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { ToastHost } from "./components/Toast";
import { isDemo, loadDemoUser } from "./demo";

/**
 * 登录 + 角色校验：未登录跳登录页，角色不在允许列表内则回到该角色首页
 * （如学生手输 /manage/accounts 会被送回 /exams）。
 */
function RequireRole({ roles, children }: { roles: Role[]; children: React.ReactNode }) {
    const location = useLocation();
    const user = useSelector((s: Store) => s.user);
    if (!isAuthenticated()) {
        return <Redirect to={{ pathname: Routes.login, state: { from: location.pathname } }}/>;
    }
    if (!user) {
        return <div className="student-page"/>;
    }
    if (!roles.includes(user.role)) {
        return <Redirect to={roleHome(user.role)}/>;
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
            <Route exact path={Routes.register} component={RegisterPage}/>
            <Route exact path="/" component={HomeRedirect}/>

            <Route exact path={Routes.examList}
                   render={() => <RequireRole roles={["student"]}><ExamListPage/></RequireRole>}/>
            <Route exact path="/exams/:examId/precheck"
                   render={() => <RequireRole roles={["student"]}><PrecheckPage/></RequireRole>}/>
            <Route exact path="/exams/:examId/workbench"
                   render={() => <RequireRole roles={["student"]}><WorkbenchPage/></RequireRole>}/>
            <Route exact path="/exams/:examId/result"
                   render={() => <RequireRole roles={["student"]}><ResultPage/></RequireRole>}/>
            <Route exact path="/exams/:examId/report"
                   render={() => <RequireRole roles={["student"]}><ReportPage/></RequireRole>}/>

            <Route exact path={Routes.examManage}
                   render={() => <RequireRole roles={["teacher", "admin"]}><ExamManagePage/></RequireRole>}/>
            <Route exact path={Routes.examCreate}
                   render={() => <RequireRole roles={["teacher", "admin"]}><ExamCreatePage/></RequireRole>}/>
            <Route exact path="/manage/:examId/edit"
                   render={() => <RequireRole roles={["teacher", "admin"]}><ExamCreatePage/></RequireRole>}/>
            <Route exact path="/manage/:examId/problems"
                   render={() => <RequireRole roles={["teacher", "admin"]}><ProblemConfigPage/></RequireRole>}/>
            <Route exact path="/manage/:examId/proctor"
                   render={() => <RequireRole roles={["teacher", "admin"]}><ProctorPage/></RequireRole>}/>
            <Route exact path={Routes.problemBank}
                   render={() => <RequireRole roles={["teacher", "admin"]}><ProblemBankPage/></RequireRole>}/>
            <Route exact path={Routes.accounts}
                   render={() => <RequireRole roles={["admin"]}><AccountsPage/></RequireRole>}/>

            <Route component={NotFoundPage as React.ComponentType<RouteProps>}/>
        </Switch>
        </>
    );
}
