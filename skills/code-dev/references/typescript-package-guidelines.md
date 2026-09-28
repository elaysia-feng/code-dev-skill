# TypeScript npm 包规范

## 适用范围

本指南用于创建、维护或发布供其他项目安装的 TypeScript/JavaScript 包。应用项目、前端页面和内部模块优先沿用仓库已有目录、构建工具与模块格式；不要仅因使用 TypeScript 就把应用改造成 npm 包。

## 包入口与公开 API

- 先确认消费者使用 Node.js、浏览器打包器还是两者，以及项目现有的 ESM/CommonJS 目标。
- 新建 Node.js 包时，可用 package.json 的 exports 明确公开入口和子路径。exports 会隐藏未列出的深层路径；给已有包新增它之前，检查已被使用的导入路径，保留兼容入口，或按破坏性变更处理。
- 让 main、exports 和 types 指向实际存在且会打包的入口/声明文件；type 用来声明 .js 文件的模块格式。各字段应与构建产物和消费者目标一致。只有目标运行环境或消费者确实需要时才增加 CommonJS/ESM 双产物、兼容入口或额外构建工具。
- 公开子路径只列稳定 API；内部实现不需要为了“完整”而全部导出。

单入口 ESM 包可以采用类似配置；入口文件必须由项目构建流程生成并随包发布：

```json
{
  "name": "@scope/package",
  "version": "1.0.0",
  "type": "module",
  "exports": {
    ".": "./dist/index.js"
  },
  "types": "./dist/index.d.ts",
  "files": ["dist"]
}
```

## 类型声明

- 面向 TypeScript 消费者的包应发布可解析的声明文件。使用现有构建链生成 .d.ts，并确保它们被纳入发布内容。
- 用 package.json 的 types 指向主入口声明文件；存在多个导出入口时，按项目支持的 TypeScript/Node 解析方式，让每个入口都能解析到相符的声明。
- 声明文件依赖其他包的类型时，把消费者需要的声明依赖放在合适的 dependencies 或 peerDependencies 中，不要只放在 devDependencies。
- 仅在确实要为不同 TypeScript 版本提供不同声明时使用 typesVersions。

## 发布内容与检查

- 用 package.json 的 files 白名单控制 tarball 内容，纳入运行产物、声明文件、必要元数据、README 和许可证；不要把测试、临时构建物、私有配置或开发环境文件带入包。
- 发布前运行 npm pack --dry-run --json，检查将发布的实际文件列表；重点核对入口、声明文件、资源和子路径目标是否都存在。
- 若新增 exports 到已有包，或移除公开子路径，按消费者可见的 API 变更评估版本兼容性。

## 官方资料

- [TypeScript：发布声明文件](https://www.typescriptlang.org/docs/handbook/declaration-files/publishing.html)
- [Node.js：Package entry points 与 exports](https://nodejs.org/api/packages.html#package-entry-points)
- [npm：package.json 的 files 字段](https://docs.npmjs.com/files/package.json#files)
- [npm：npm pack 与 dry-run](https://docs.npmjs.com/cli/v11/commands/npm-pack/)
