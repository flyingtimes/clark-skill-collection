# 使用chrome的cdp协议控制浏览器
## mac下打开一个chrome的cdp实例
### 一、复制用户配置数据到本地副本
macos
```bash
cp -R ~/Library/Application\ Support/Google/Chrome/Default ./userdata
```
windows
```
xcopy  "c:\Users\13802\AppData\Local\Google\Chrome\User Data\Default" "C:\\Users\\13802\\code\\podcast-using-skill\\userdata\\Default" /S

```
> 注意：一定要先关闭所有chrome浏览器下操作，否则复制到内容是不完整的

### 二、开启新浏览器实例
#### macos
```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 --user-data-dir="$PWD/userdata"   --no-first-run   --no-default-browser-check --disable-popup-blocking --proxy-server="http://127.0.0.1:1087" --start-maximized
```
#### windows
首先检查后台进程是否存在chrome进程，如果存在则先杀掉chrome进程。然后通过下面的操作启动新的浏览器
```
"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" --remote-debugging-port=9222 --proxy-server="http://127.0.0.1:1087"  --user-data-dir="C:\\Users\\13802\\code\\podcast-using-skill\userdata"

```
这个时候命令行会返回：
```
DevTools listening on ws://127.0.0.1:9222/devtools/browser/{session-id}
```
检查9222端口是否正常开启
## 给claud code 安装chrome-dev-mcp插件
```
claude mcp add chrome-devtools -s project npx chrome-devtools-mcp@latest
```
安装完以后，会给项目目录下的.mcp.json配置文件添加一下内容
```.mcp.json 
"mcpServers": {
    "chrome-devtools": {
      "type": "stdio",
      "command": "npx",
      "args": [
      "chrome-devtools-mcp@latest",
      "--browser-url=http://127.0.0.1:9222"
      ],
      "env": {}
    }
  }          
```
> 注意：browser-url要手工加上，否则每次都会打开一个新的浏览器，而不是前面事先打开的浏览器。打开事先准备好的浏览器并登陆好你的账户，可以节约很多账号登陆相关的工作。如果每次打开新的窗口，则需要检查.claude.json文件的配置是否存在错误，这个需要自己检查清楚，一般是有重复的声明。
## 在claude code 的使用示例
抓取任务
> 打开https://www.theatlantic.com/latest/,找到最热门的十篇文章和链接，并逐一打开链接获取正文内容，写入output/文件夹中，生成的文件名为{title}.txt
> 
为了过程的流畅，需要打开claude的选项
```
claude --dangerously-skip-permissions -p "打开https://www.theatlantic.com/latest/,找到最新的3篇文章,参考@README_API.md的指引，将标题、副标题、作者、url、记录时间通过接口写入"
```
翻译任务
```
claude --dangerously-skip-permissions -p "translate 翻译output文件夹中的所有文件内容为中文，并写入到output/{中文title}.txt" 
```
获取正文内容
```
claude --dangerously-skip-permissions -p "根据指引  @README_API.md ，通过接口读取所有记录，对每个记录检查content是否为空，如果为空，则用 skill: crawl
  访问url，获取正文内容，并将正文内容写入content字段，直到所有content字段都不为空。"
```