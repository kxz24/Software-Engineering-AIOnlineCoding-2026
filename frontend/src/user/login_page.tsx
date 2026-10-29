import React from "react";
import {
    Button,
    CircularProgress,
    createStyles,
    TextField,
    Typography,
    useTheme
} from "@material-ui/core";
import {Strings, format, translate} from "../strings";
import {makeStyles} from "@material-ui/core/styles";
import {login} from "../backend";
import {Store, tokenSlice} from "../store";
import {Alert} from "@material-ui/lab";
import {Redirect} from "react-router-dom";
import {useDispatch, useSelector} from "react-redux";

const useStyles = makeStyles((theme) => createStyles({
    list: {
        padding: "20px",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        "& .MuiTextField-root, .MuiButton-root": {
            margin: theme.spacing(1),
            width: "30ch",
        },
    },
    subtitle: {
        color: theme.palette.text.secondary,
        marginBottom: theme.spacing(1),
    },
}));

/**
 * 登录页。
 * 角色不由用户选择，而是由账号在数据库中的 role 字段决定，
 * 登录成功后首页按角色展示对应内容。
 */
export function LoginPage() {
    const classes = useStyles(useTheme());
    const token = useSelector((store: Store) => store.token);
    const dispatch = useDispatch();
    const [username, setUsername] = React.useState("");
    const [password, setPassword] = React.useState("");
    const [loggingIn, setLoggingIn] = React.useState(false);
    const [loggedIn, setLoggedIn] = React.useState(token != null);
    const [errorMessage, setErrorMessage] = React.useState(null as (string | null));

    const canSubmit = username !== "" && password !== "" && !loggingIn && !loggedIn;

    const handleClick = () => {
        if (!canSubmit) {
            return;
        }
        setLoggingIn(true);
        setErrorMessage(null);
        login(username, password).then((result) => {
            setLoggingIn(false);
            if (result.success) {
                dispatch(tokenSlice.actions.setToken(result.jwt));
                setLoggedIn(true);
            } else {
                setErrorMessage(result.message);
            }
        }, (reason) => {
            setLoggingIn(false);
            setErrorMessage(translate(String(reason)));
        });
    };

    const handleKeyDown = (evt: React.KeyboardEvent) => {
        if (evt.key === "Enter") {
            handleClick();
        }
    };

    return <div className={classes.list}>
        {loggedIn ? <Redirect to="/"/> : undefined}
        <Typography variant="h4">{Strings["login/title"]}</Typography>
        <Typography variant="body2" className={classes.subtitle}>
            {Strings["login/subtitle"]}
        </Typography>
        <TextField
            required
            id="username"
            label={Strings["login/username"]}
            onChange={(evt) => setUsername(evt.target.value)}
            onKeyDown={handleKeyDown}
        />
        <TextField
            required
            id="password"
            label={Strings["login/password"]}
            type="password"
            onChange={(evt) => setPassword(evt.target.value)}
            onKeyDown={handleKeyDown}
        />
        <Button onClick={handleClick}
                disabled={!canSubmit}
                variant="contained"
                color={canSubmit ? "primary" : "default"}>
            {loggingIn ? <CircularProgress size="1em" color="primary"/> : undefined}
            {Strings["login/login"]}
            {loggingIn ? <span style={{"width": "1em"}}/> : undefined}
        </Button>
        {errorMessage ?
            <Alert severity="error">
                {format("login/failed", {"message": errorMessage})}
            </Alert>
            : undefined}
    </div>;
}
