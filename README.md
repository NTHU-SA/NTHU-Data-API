# NTHU-Data-API
[![CodeFactor](https://www.codefactor.io/repository/github/nthu-sa/nthu-data-api/badge)](https://www.codefactor.io/repository/github/nthu-sa/nthu-data-api)  [![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)  [![Smokeshow coverage](https://coverage-badge.samuelcolvin.workers.dev/NTHU-SA/NTHU-Data-API.svg)](https://coverage-badge.samuelcolvin.workers.dev/redirect/NTHU-SA/NTHU-Data-API)
## Introduction
This is a project for NTHU students to get data from NTHU website.

## Usage
### Install
```sh
pip3 install -r requirements.txt
```
### Config
```sh
cp .env.template .env
```
### Run
```sh
python3 main.py
```

## Notes
### Commit:
#### Type:
- feat: 新增/修改功能 (feature)。
- fix: 修補 bug (bug fix)。
- docs: 文件 (documentation)。
- style: 格式 (不影響程式碼運行的變動 white-space, formatting, missing semi colons, etc)。
- refactor: 重構 (既不是新增功能，也不是修補 bug 的程式碼變動)。
- perf: 改善效能 (A code change that improves performance)。
- test: 增加測試 (when adding missing tests)。
- chore: 建構程序或輔助工具的變動 (maintain)。
- revert: 撤銷回覆先前的 commit 例如：revert: type(scope): subject (回覆版本：xxxx)。
#### Message Format:
```sh
<type>(<scope>): <subject>
<BLANK LINE>
<body>
<BLANK LINE>
<footer>
```
#### Message Example:
```sh
feat(README.md): add commit type and commit message format
```
#### Reference
- [Git Commit Message Convention](https://gist.github.com/stephenparish/9941e89d80e2bc58a153)
- [Git Commit Message 這樣寫會更好，替專案引入規範與範例](https://wadehuanglearning.blogspot.com/2019/05/commit-commit-commit-why-what-commit.html)

## Credit
- NTHUSA 32nd

## License
[MIT](https://choosealicense.com/licenses/mit/)