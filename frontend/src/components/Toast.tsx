import React, { useEffect, useRef, useState } from "react";

export type ToastKind = "info" | "success" | "warning";

interface ToastMessage {
    id: number;
    text: string;
    kind: ToastKind;
}

let emitter: ((text: string, kind: ToastKind) => void) | null = null;

/** 在任意位置弹出一条轻提示（原型里的 toast 交互） */
export function toast(text: string, kind: ToastKind = "info") {
    if (emitter) {
        emitter(text, kind);
    }
}

const KindColor: Record<ToastKind, string> = {
    info: "#2563eb",
    success: "#047857",
    warning: "#b45309",
};

/**
 * 轻提示容器，挂在 App 根节点上。
 * 使用全局 toast() 触发，避免每个页面都写一遍状态。
 */
export function ToastHost() {
    const [messages, setMessages] = useState<ToastMessage[]>([]);
    const seed = useRef(0);

    useEffect(() => {
        emitter = (text: string, kind: ToastKind) => {
            const id = ++seed.current;
            setMessages(current => [...current, { id, text, kind }]);
            window.setTimeout(() => {
                setMessages(current => current.filter(message => message.id !== id));
            }, 2600);
        };
        return () => {
            emitter = null;
        };
    }, []);

    if (messages.length === 0) {
        return null;
    }

    return (
        <div style={{
            position: "fixed",
            top: 74,
            left: "50%",
            transform: "translateX(-50%)",
            zIndex: 999,
            display: "flex",
            flexDirection: "column",
            gap: 8,
            alignItems: "center",
        }}>
            {messages.map(message => (
                <div key={message.id}
                     className="fade-in"
                     style={{
                         background: "#fff",
                         border: "1px solid #e2e8f0",
                         borderLeft: `3px solid ${KindColor[message.kind]}`,
                         borderRadius: 8,
                         boxShadow: "0 10px 24px rgba(15,23,42,.10)",
                         padding: "9px 14px",
                         fontSize: 12,
                         color: "#334155",
                     }}>
                    {message.text}
                </div>
            ))}
        </div>
    );
}
