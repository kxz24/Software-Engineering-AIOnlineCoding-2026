import {useDispatch, useSelector} from "react-redux";
import {Store, userSlice} from "../store";
import React from "react";
import {logout, user} from "../backend";
import {Button, createStyles, useTheme} from "@material-ui/core";
import {makeStyles} from "@material-ui/core/styles";
import AccountCircleIcon from "@material-ui/icons/AccountCircle";
import {Strings} from "../strings";
import {Link} from "react-router-dom";
import {LocalUrls} from "../urls";
import {roleLabel} from "../roles";

const useStyles = makeStyles((theme) => createStyles({
    button: {
        marginLeft: "auto",
        fontSize: "1em",
        transition: "background-color ease-out 200ms",
        "& .link": {
            color: theme.palette.primary.contrastText,
            textDecoration: "none",
        },
        "& .MuiButton-label": {
            fontSize: "1.15em",
            alignItems: "stretch",
        }
    }
}));

/**
 * 顶端工具条右侧的用户信息。
 * 持有令牌时拉取一次当前用户（包含角色）写入 Redux；
 * 令牌失效（401）则自动登出。
 */
export function UserBarInfo() {
    const classes = useStyles(useTheme());
    const token = useSelector((state: Store) => state.token);
    const userInfo = useSelector((state: Store) => state.user);
    const dispatch = useDispatch();

    React.useEffect(() => {
        if (token == null) {
            // 已登出，清掉残留的用户信息
            dispatch(userSlice.actions.updateUserStatus(null));
            return;
        }
        user().then((result) => {
            if (result.success) {
                dispatch(userSlice.actions.updateUserStatus(result.user));
            } else {
                dispatch(userSlice.actions.updateUserStatus(null));
                if (!result.authorized) {
                    // 令牌过期或无效，直接登出
                    logout(dispatch);
                }
            }
        }, () => {
            dispatch(userSlice.actions.updateUserStatus(null));
        });
    }, [token]);

    let display: string;
    if (userInfo) {
        display = `${userInfo.nickname}（${roleLabel(userInfo.role)}）`;
    } else {
        display = token ? "" : Strings["main/not_logged_in"];
    }

    return <span className={classes.button}>
        <Button color="inherit" component={Link} to={LocalUrls.home()}>
            <AccountCircleIcon/><span>{display}</span>
        </Button>
    </span>;
}
