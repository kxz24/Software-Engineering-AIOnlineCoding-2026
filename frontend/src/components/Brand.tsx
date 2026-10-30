import React from "react";

/** 平台 Logo：蓝色圆角方块 + 白色终端符号 */
export function Logo({ size = 30 }: { size?: number }) {
    return (
        <div className="logo" style={size === 30 ? undefined : { width: size, height: size }}>
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="#ffffff" strokeWidth="2.2"
                 strokeLinecap="round" strokeLinejoin="round">
                <path d="M4 7l4 5-4 5"/>
                <path d="M12 17h8"/>
            </svg>
        </div>
    );
}

/** 学生端顶栏 / 登录页 Logo 与站名 */
export function Brand({ small = false, subtitle }: { small?: boolean; subtitle?: string }) {
    return (
        <div className="brand">
            <Logo/>
            <div>
                <div className={"brand-name" + (small ? " small" : "")}>
                    {small ? "AI Coding" : "AI Coding 考试平台"}
                </div>
                {subtitle && <div className="brand-sub">{subtitle}</div>}
            </div>
        </div>
    );
}
