import React from "react";
import { useHistory } from "react-router-dom";
import { Icon } from "./Icon";

interface Props {
    /** 没有站内历史时的回退地址；默认回到角色首页（/ 会按角色重定向） */
    fallback?: string;
    label?: string;
}

/**
 * 统一返回按钮：优先浏览历史后退，直接打开页面时回退到角色首页。
 * 放在学生端 / 教师端外壳里，所有使用布局的页面都会自动拥有返回入口。
 */
export function BackButton({ fallback = "/", label = "返回" }: Props) {
    const history = useHistory();

    const handleBack = () => {
        if (window.history.length > 1) {
            history.goBack();
        } else {
            history.push(fallback);
        }
    };

    return (
        <button type="button"
                className="btn btn-ghost btn-sm"
                title="返回上一页"
                onClick={handleBack}
                style={{ whiteSpace: "nowrap" }}>
            <Icon name="arrow-left" size={13}/>{label}
        </button>
    );
}
