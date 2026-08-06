# 中间结论文档区

本目录只服务尚在探索、尚未达到冻结条件的实验路径。它不是临时草稿垃圾桶，也不能替代 Git。

## 生命周期

1. **提出路径**：新建一个按物理问题命名的文档，不使用 `v1/v2/final/latest`；
2. **预注册**：写清问题、假设、输入、固定量、预期可证伪结果、验收门限和停止条件；
3. **逐次记录**：每轮追加日期、Git SHA、配置、产物路径、观察和与预期的差异；不得覆盖失败结果；
4. **形成结论**：明确哪些结论成立、被否定或仍不可识别；
5. **同步主结论**：把完整的最终结论和限制同步到 `../MAIN_CONCLUSIONS.md`；
6. **关闭路径**：文档保留并标记 `concluded` 或 `abandoned_with_evidence`，不改名为 `final`，不删除过程。

## 文档头必填字段

```text
status: proposed | active | blocked | concluded | abandoned_with_evidence
opened_at:
last_updated_at:
owner:
base_git_commit:
question:
pre_registered_acceptance:
main_conclusion_sync:
```

## 当前路径

|文档|状态|问题|主结论同步|
|---|---|---|---|
|[`MECHANICAL_TRANSFER_PATH.md`](MECHANICAL_TRANSFER_PATH.md)|`concluded`|面积、界面力和全局载荷份额能否独立构成正向 IOP 模型|已同步至 `../MAIN_CONCLUSIONS.md`|

下一条建议路径是“工作点小扰动切线刚度与全局载荷份额独立预测”。启动前应另建文档并预注册压力点、扰动幅度、反力分解和验收标准。
