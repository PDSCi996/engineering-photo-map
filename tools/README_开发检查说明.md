# 开发检查工具说明 v0.1.1

## 一、用途

本目录用于保存工程照片地图管理系统的开发检查工具。

主要检查：

1. 项目目录是否完整
2. `.gitignore` 是否遗漏重要目录
3. `.env` 是否可能被误提交
4. Python 后端 / worker 代码基础检查
5. Python 安全风险扫描
6. Python 依赖漏洞扫描
7. pytest 自动测试
8. 前端 npm audit / npm run build
9. 合并冲突、debugger、eval、硬编码密码等明显问题

## 二、第一次使用

先双击：

```text
tools/install_dev_tools.cmd
```

## 三、每次开发完成后使用

双击：

```text
tools/check_all.cmd
```

## 四、检查结果

```text
reports/dev-check-日期时间.md
logs/dev-check-raw-日期时间.txt
```

## 五、本版修复

v0.1.1 修复：

```text
1. 工具未安装时不再误判为代码失败
2. echo ====== 不再误判为 Git 合并冲突
3. 默认不扫描 tools 自身
4. .gitignore 检查兼容有无斜杠写法
5. npm 不存在只作为环境提示
```
