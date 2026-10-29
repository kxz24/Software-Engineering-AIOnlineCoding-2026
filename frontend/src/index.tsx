import "normalize.css/normalize.css";
import React from "react";
import ReactDOM from 'react-dom';
import {
    AppBar,
    createMuiTheme,
    Drawer,
    IconButton,
    Theme,
    ThemeProvider,
    Toolbar,
    Typography
} from "@material-ui/core";
import {Strings} from "./strings";
import {LoginPage} from "./user/login_page";
import {BrowserRouter, Route, Switch} from 'react-router-dom';
import {HomePage} from "./mainpage/homepage";
import {Provider} from "react-redux";
import {store} from "./store";
import MenuIcon from "@material-ui/icons/Menu";
import {UserBarInfo} from "./user/user_bar_view";
import {DrawerContents} from "./mainpage/drawer";
import {PageNotFoundPage} from "./page_not_found/page_not_found";

/**
 * 应用外壳：顶部工具条 + 侧边抽屉 + 路由。
 * 目前只有首页与登录页，其余角色工作台后续在此扩展。
 */
class App extends React.Component<{}, { drawerOpen: boolean }> {
    theme: Theme;

    constructor(props: {}) {
        super(props);
        this.theme = createMuiTheme();
        this.state = {
            drawerOpen: false,
        };
    }

    render(): React.ReactNode {
        return (
            <ThemeProvider theme={this.theme}>
                <div style={{
                    color: this.theme.palette.text.primary,
                    backgroundColor: this.theme.palette.background.default,
                    "minHeight": "100%"
                }}>
                    <BrowserRouter>
                        <AppBar position="fixed">
                            <Toolbar>
                                <IconButton color="inherit"
                                            aria-label="open drawer"
                                            onClick={() => this.setState({drawerOpen: true})}
                                            edge="start"
                                            style={{
                                                marginRight: this.theme.spacing(2),
                                            }}
                                >
                                    <MenuIcon/>
                                </IconButton>
                                <Typography variant="h6" color="inherit">
                                    {Strings["main/title"]}
                                </Typography>
                                <UserBarInfo/>
                            </Toolbar>
                        </AppBar>
                        <Toolbar/>

                        <Drawer anchor="left" open={this.state.drawerOpen}
                                onClose={() => this.setState({drawerOpen: false})}>
                            <div onClick={() => this.setState({drawerOpen: false})}>
                                <DrawerContents/>
                            </div>
                        </Drawer>

                        <div style={{height: this.theme.spacing(1)}}/>
                        <div style={{overflow: "auto", height: `calc(100vh - ${64 + this.theme.spacing(2)}px)`}}>
                            <Switch>
                                <Route exact path="/" component={HomePage}/>
                                <Route path="/login" component={LoginPage}/>
                                <Route component={PageNotFoundPage}/>
                            </Switch>
                        </div>
                        <div style={{height: this.theme.spacing(1)}}/>
                    </BrowserRouter>
                </div>
            </ThemeProvider>
        );
    }
}

ReactDOM.render(
    (<Provider store={store}><App/></Provider>),
    document.getElementById('root')
);
