import React from "react";
import {
    Button,
    Chip,
    CircularProgress,
    Container,
    createStyles,
    Paper,
    Typography,
    useTheme
} from "@material-ui/core";
import {makeStyles} from "@material-ui/core/styles";
import {useDispatch, useSelector} from "react-redux";
import {Link} from "react-router-dom";
import {Store} from "../store";
import {Strings, format} from "../strings";
import {LocalUrls} from "../urls";
import {logout} from "../backend";
import {Role, Roles, roleLabel} from "../roles";

const useStyles = makeStyles(theme => createStyles({
    main: {
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        paddingTop: theme.spacing(6),
    },
    card: {
        width: "100%",
        maxWidth: "640px",
        padding: theme.spacing(4),
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: theme.spacing(2),
    },
    roleRow: {
        display: "flex",
        alignItems: "center",
        gap: theme.spacing(1),
    },
    description: {
        color: theme.palette.text.secondary,
        textAlign: "center",
    },
}));

/**
 * 首页。
 * 未登录：提示去登录；已登录：展示当前身份与该角色的职责说明。
 * 后续各角色的工作台入口从这里扩展。
 */
export function HomePage() {
    const classes = useStyles(useTheme());
    const token = useSelector((state: Store) => state.token);
    const userInfo = useSelector((state: Store) => state.user);
    const dispatch = useDispatch();

    // 尚未登录
    if (token == null) {
        return <Container maxWidth="lg">
            <div className={classes.main}>
                <Paper className={classes.card} elevation={2}>
                    <Typography variant="h4" component="h1">
                        {Strings["home/not_logged_in_title"]}
                    </Typography>
                    <Typography className={classes.description}>
                        {Strings["home/not_logged_in_content"]}
                    </Typography>
                    <Button variant="contained" color="primary"
                            component={Link} to={LocalUrls.login()}>
                        {Strings["home/go_login"]}
                    </Button>
                </Paper>
            </div>
        </Container>;
    }

    // 已登录，但用户信息还在请求中
    if (userInfo == null) {
        return <Container maxWidth="lg">
            <div className={classes.main}><CircularProgress/></div>
        </Container>;
    }

    const meta = Roles[userInfo.role as Role];

    return <Container maxWidth="lg">
        <div className={classes.main}>
            <Paper className={classes.card} elevation={2}>
                <Typography variant="h4" component="h1">
                    {format("home/welcome", {"nickname": userInfo.nickname})}
                </Typography>
                <div className={classes.roleRow}>
                    <Chip color="primary" label={roleLabel(userInfo.role)}/>
                    <Typography variant="body2" color="textSecondary">
                        {format("home/role", {"role": roleLabel(userInfo.role)})}
                    </Typography>
                </div>
                <Typography className={classes.description}>
                    {meta ? meta.description : ""}
                </Typography>
                <Button variant="outlined" color="secondary"
                        onClick={() => logout(dispatch)}>
                    {Strings["home/logout"]}
                </Button>
            </Paper>
        </div>
    </Container>;
}
