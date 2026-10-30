/* 页面冒烟测试：用 mock 数据把每个页面渲染一遍，确保组件不抛异常。
 * 运行方式：npm test -- --watchAll=false */
import React from "react";
import ReactDOM from "react-dom";
import { Provider } from "react-redux";
import { MemoryRouter, Route } from "react-router-dom";
import { store } from "./store";
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

const Pages: { name: string; path: string; component: React.ComponentType<any> }[] = [
    { name: "login", path: "/login", component: LoginPage },
    { name: "exam-list", path: "/exams", component: ExamListPage },
    { name: "precheck", path: "/exams/:examId/precheck", component: PrecheckPage },
    { name: "workbench", path: "/exams/:examId/workbench", component: WorkbenchPage },
    { name: "result", path: "/exams/:examId/result", component: ResultPage },
    { name: "report", path: "/exams/:examId/report", component: ReportPage },
    { name: "manage", path: "/manage", component: ExamManagePage },
    { name: "create", path: "/manage/new", component: ExamCreatePage },
    { name: "problems", path: "/manage/:examId/problems", component: ProblemConfigPage },
    { name: "proctor", path: "/manage/:examId/proctor", component: ProctorPage },
    { name: "not-found", path: "/whatever", component: NotFoundPage },
];

describe("页面冒烟渲染", () => {
    Pages.forEach(page => {
        it(`renders ${page.name}`, () => {
            const entry = page.path.replace(":examId", "exam-mid-2026");
            const container = document.createElement("div");
            ReactDOM.render(
                <Provider store={store}>
                    <MemoryRouter initialEntries={[entry]}>
                        <Route path={page.path} component={page.component}/>
                    </MemoryRouter>
                </Provider>,
                container
            );
            expect(container.innerHTML.length).toBeGreaterThan(200);
            ReactDOM.unmountComponentAtNode(container);
        });
    });
});
