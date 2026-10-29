import React from "react";
import {
    Button,
    createStyles,
    Divider,
    List,
    ListItem,
    ListItemIcon,
    ListItemText,
    useTheme
} from "@material-ui/core";
import {makeStyles} from "@material-ui/core/styles";
import {useDispatch, useSelector} from "react-redux";
import {Link} from "react-router-dom";
import {Store} from "../store";
import {LocalUrls} from "../urls";
import AccountCircleIcon from "@material-ui/icons/AccountCircle";
import HomeIcon from "@material-ui/icons/Home";
import ExitToAppIcon from "@material-ui/icons/ExitToApp";
import PersonIcon from "@material-ui/icons/Person";
import {Strings} from "../strings";
import {logout} from "../backend";

const drawerWidth = 240;

const useStyles = makeStyles(theme => createStyles({
    list: {
        width: drawerWidth,
    },
    drawerHeader: {
        display: "flex",
        alignItems: "center",
        padding: theme.spacing(0, 1),
        // 让内容避开顶部 AppBar
        ...theme.mixins.toolbar,
        justifyContent: "center",
    },
    verticalCenter: {
        display: "flex",
        alignItems: "center",
    }
}));

/**
 * 抽屉导航。
 * 当前只有首页与登录/退出，后续按角色补充入口。
 */
export function DrawerContents() {
    const classes = useStyles(useTheme());
    const userInfo = useSelector((store: Store) => store.user);
    const dispatch = useDispatch();

    return <React.Fragment>
        <div className={classes.drawerHeader}>
            <Button color="inherit" component={Link} to={LocalUrls.home()}>
                <span className={classes.verticalCenter}>
                    {userInfo ?
                        <React.Fragment>
                            <PersonIcon fontSize="small"/>{userInfo.nickname}
                        </React.Fragment>
                        : Strings["main/not_logged_in"]}
                </span>
            </Button>
        </div>
        <Divider/>
        <List className={classes.list}>
            <ListItem button component={Link} to={LocalUrls.home()}>
                <ListItemIcon><HomeIcon/></ListItemIcon>
                <ListItemText primary={Strings["drawer/home"]}/>
            </ListItem>
            {userInfo ?
                <ListItem button onClick={() => logout(dispatch)}>
                    <ListItemIcon><ExitToAppIcon/></ListItemIcon>
                    <ListItemText primary={Strings["drawer/logout"]}/>
                </ListItem>
                :
                <ListItem button component={Link} to={LocalUrls.login()}>
                    <ListItemIcon><AccountCircleIcon/></ListItemIcon>
                    <ListItemText primary={Strings["drawer/login"]}/>
                </ListItem>
            }
        </List>
    </React.Fragment>;
}
