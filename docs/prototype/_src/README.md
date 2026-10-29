# 生成脚本

修改页面内容后，在 `产品原型` 目录运行：

```bash
python -I _src/build_pages.py
python -I _src/build_modao.py
```

- `build_pages.py`：生成 `本地预览版/`，保留页面之间的 `<a>` 链接，方便浏览器点着走。
- `build_modao.py`：从 `本地预览版/` 生成 `墨刀导入版/`，去掉所有 `href`，避免墨刀预览报「没找到链接」。

`预览图/` 不自动生成；需要更新时，用 Edge headless 对 `本地预览版/*.html` 重新截图即可。
