import React from "react";
import { Link } from "react-router-dom";
import { Icon } from "../components/Icon";
import { Routes } from "../api/urls";

/** 404：保持与原型的卡片风格一致 */
export function NotFoundPage() {
    return (
        <div style={{
            minHeight: "100vh",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: 24,
        }}>
            <div className="card" style={{ width: 420, padding: "30px 32px", textAlign: "center" }}>
                <div className="page-title" style={{ marginBottom: 6 }}>页面不存在</div>
                <div className="page-sub" style={{ marginBottom: 18 }}>
                    你访问的页面可能已经移动或尚未开放。
                </div>
                <Link className="btn btn-primary" to={Routes.examList}>
                    <Icon name="arrow-left" size={14}/>返回我的考试
                </Link>
            </div>
        </div>
    );
}
