# Mermaid 加载问题修复说明

## 问题描述
在浏览器中打开 `mermaid_test.html` 时出现错误：
```
Failed to load resource: net::ERR_NAME_NOT_RESOLVED
Uncaught ReferenceError: mermaid is not defined
```

**原因分析：**
1. CDN 资源 `https://cdn.jsdelivr.net/npm/mermaid@10.6.1/dist/mermaid.min.js` 无法解析
2. 可能是网络问题、DNS 解析问题或 CDN 服务不可用

## 解决方案

我已创建三个版本的测试文件，按推荐顺序测试：

### 方案 1：使用国内 CDN（推荐）⭐
**文件：** `mermaid_test_cn_cdn.html`

**特点：**
- 使用国内 CDN（lib.baomitu.com）
- 访问速度快，稳定性高
- 适合中国大陆网络环境

**使用方法：**
```bash
# 直接在浏览器中打开
open mermaid_test_cn_cdn.html  # Mac
start mermaid_test_cn_cdn.html  # Windows
```

---

### 方案 2：多 CDN 自动备选
**文件：** `mermaid_test_multi_cdn.html`

**特点：**
- 自动尝试多个 CDN 源（按优先级）
- 包含详细的加载诊断信息
- 实时显示加载状态

**CDN 源列表：**
1. jsDelivr (国际)
2. unpkg (国际)
3. cdnjs (国际)

**使用方法：**
```bash
open mermaid_test_multi_cdn.html
```

---

### 方案 3：原文件修复
**文件：** `mermaid_test.html`（已修复）

**特点：**
- 使用 jsdelivr 和 unpkg 作为备选
- 如果第一个 CDN 失败，自动尝试第二个

**使用方法：**
```bash
open mermaid_test.html
```

---

## 测试步骤

1. **推荐优先测试方案 1（国内 CDN）**
   ```bash
   open mermaid_test_cn_cdn.html
   ```

2. **如果方案 1 仍有问题，尝试方案 2**
   ```bash
   open mermaid_test_multi_cdn.html
   ```

3. **查看浏览器控制台诊断信息**
   - 按 `F12` 打开开发者工具
   - 查看 Console 标签页的详细日志

4. **在线测试（备选）**
   - 访问 https://mermaid.live/
   - 将 Mermaid 代码粘贴进去测试

---

## 诊断命令

如果以上方案都无法解决，可以运行诊断：

```bash
# 测试网络连接
ping cdn.jsdelivr.net
ping unpkg.com
ping cdnjs.cloudflare.com
ping lib.baomitu.com

# 测试 DNS 解析
nslookup cdn.jsdelivr.net
nslookup lib.baomitu.com

# 使用 curl 测试 CDN
curl -I https://lib.baomitu.com/mermaid/10.6.1/mermaid.min.js
```

---

## 修复到 history_manager.py

如果找到可用的 CDN，可以更新 `history_manager.py` 中的 CDN URL：

```python
# 在 export_pipeline_html() 方法中找到这一行
# <script src="https://cdn.jsdelivr.net/npm/mermaid@10.9.5/dist/mermaid.min.js"></script>

# 替换为可用的 CDN（例如国内 CDN）
# <script src="https://lib.baomitu.com/mermaid/10.6.1/mermaid.min.js"></script>
```

---

## 其他解决方案

### 1. 离线模式（下载到本地）
```bash
# 下载 mermaid.js 到本地
wget https://lib.baomitu.com/mermaid/10.6.1/mermaid.min.js -o static/mermaid.min.js

# 修改 HTML 引用本地文件
# <script src="./static/mermaid.min.js"></script>
```

### 2. 使用代理
如果网络受限，可以配置系统代理或使用 VPN。

### 3. 切换 Mermaid 版本
尝试使用其他版本：
- 10.9.1
- 10.8.0
- 10.6.1（当前版本）

---

## 文件清单

| 文件名 | 说明 | 推荐度 |
|--------|------|--------|
| `mermaid_test_cn_cdn.html` | 国内 CDN 版本 | ⭐⭐⭐⭐⭐ |
| `mermaid_test_multi_cdn.html` | 多 CDN 备选 + 诊断 | ⭐⭐⭐⭐ |
| `mermaid_test.html` | 原文件修复版 | ⭐⭐⭐ |

---

## 预期结果

正常情况下，浏览器中应该显示：
- ✅ 绿色状态提示 "Mermaid 加载成功"
- ✅ 流程图正常渲染（显示节点和连线）
- ✅ 样式正确（绿色节点、蓝色节点）

---

## 需要帮助？

如果所有方案都无法解决问题：
1. 检查网络连接是否正常
2. 尝试使用不同的浏览器（Chrome、Firefox、Edge）
3. 清除浏览器缓存后重试
4. 检查防火墙或代理设置
