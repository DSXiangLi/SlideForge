/* ============================================================
   pptx-html 编辑器门面：window.pptxMcp（MCP Apps View 侧）
   本文件由 tools/build_ext_apps_bundle.py 追加到官方 View SDK bundle 之后
   （同一 module 作用域，可直接使用其 `App` / `PostMessageTransport`）。
   editor.html 只依赖这个门面，不依赖 SDK 细节；宿主能力一律"试调用 + try/catch"
   （设计 §3.2 写法纪律：存在性检测在沙箱里是伪检测）。
   ============================================================ */
(function(){
  var App = __ext.App, PostMessageTransport = __ext.PostMessageTransport;
  var api = window.pptxMcp || (window.pptxMcp = {});
  var app = new App({ name: "pptx-html-editor", version: VIEW_VERSION });

  /* 引导脚本早于本模块执行，因此这里必须**在 connect 之前**接上引导期注册的回调
     （SDK 规定 handler 要在 connect 前注册，否则可能漏掉通知；且对 onteardown 这类
     一次性事件，握手完成后注册会被 SDK 直接抛错）。包装函数始终转发到 api 上的最新
     回调，所以引导期与安装后注册的行为一致。 */
  app.onteardown = async function(){
    var handler = api.__teardown;
    if (typeof handler !== "function") return {};
    try { await handler(); return {}; }
    catch(e){ return { error: String((e && e.message) || e) }; }
  };
  /* 宿主载荷可能在 editor.html 注册回调**之前**到达（引导脚本早于 bundle 执行，注册点在脚本中段），
     这正是 `bridge_mcp.py` 注释里记过的"编辑器一直停在等待宿主下发会话"。因此这里缓冲最后一次
     tool-input / tool-result，注册时立即重放（注册只发生一次，重放是幂等的）。 */
  function deliver(kind, params){
    if (kind === "input") api.__lastToolInput = params; else api.__lastToolResult = params;
    var handler = kind === "input" ? api.__toolInput : api.__toolResult;
    if (typeof handler !== "function") return;      /* 还没注册 → 留着，注册时重放 */
    try { handler(params); } catch(e){ /* 观察者异常不得打断协议 */ }
  }
  app.ontoolinput = function(params){ deliver("input", params); };
  app.ontoolresult = function(params){ deliver("result", params); };

  /* 宿主载荷差异（2026-10-22 复读宿主源码所得）：
     - 旧行为：宿主把工具结果压成纯文本经 content 传给 View（`mcp_result_to_ui_text`）；
     - 新行为（SproutHarness 1022 起）：传**完整 CallToolResult**，含 structuredContent / isError / _meta。
     两条路都要能用：优先 structuredContent（更权威，且带 isError），回落到解析 content 文本
     ——我们的 app-only 工具本就返回 JSON 字符串。注意 FastMCP 对字符串返回值会包一层
     `{result: "<json>"}`，必须拆开；而 dict 返回值（如 get_status）本身就是对象，原样使用。 */
  function unwrapStructured(payload){
    if (!payload || typeof payload !== "object") return null;
    var keys = Object.keys(payload);
    if (keys.length === 1 && keys[0] === "result"){
      var inner = payload.result;
      if (typeof inner === "string"){
        try { return JSON.parse(inner); } catch(e){ return null; }
      }
      return inner === undefined ? null : inner;
    }
    return payload;
  }

  function textOf(result){
    var blocks = (result && result.content) || [];
    return blocks.filter(function(b){ return b && b.type === "text"; })
                 .map(function(b){ return b.text; }).join("");
  }

  /* MCP Python SDK 会把**任何**工具异常重新包成
     `Error executing tool <name>: <原消息>`（mcp/server/fastmcp/tools/base.py），
     所以我们抛出的 `{"ok":false,...}` JSON 会带上这段散文前缀，且 isError 分支
     按约定不带 structuredContent。必须先剥前缀再解析，否则 error.code / details 全丢。 */
  function stripToolPrefix(text){
    return String(text == null ? "" : text).replace(/^Error executing tool [^:\n]*:\s*/, "");
  }

  function errorDetail(result, payload, text){
    var candidates = [];
    if (payload && payload.error) candidates.push(payload.error);
    var raw = stripToolPrefix(text);
    try { var parsed = raw ? JSON.parse(raw) : null; if (parsed && parsed.error) candidates.push(parsed.error); } catch(e){}
    /* 前缀之外还可能夹着别的散文（宿主包装/多段文本）：退一步只取首个 JSON 对象 */
    if (!candidates.length){
      var loose = /\{[\s\S]*\}/.exec(raw);
      if (loose){
        try { var boxed = JSON.parse(loose[0]); if (boxed && boxed.error) candidates.push(boxed.error); } catch(e){}
      }
    }
    return candidates[0] || null;
  }

  function parseToolResult(result){
    var text = textOf(result);
    var payload = unwrapStructured(result && result.structuredContent);
    if (payload === null){
      try { payload = text ? JSON.parse(stripToolPrefix(text)) : null; } catch(e){ payload = null; }
    }
    if (result && result.isError){
      var detail = errorDetail(result, payload, text);
      var err = new Error((detail && detail.message) || stripToolPrefix(text) || "工具调用失败");
      err.code = detail && detail.code;
      err.details = detail && detail.details;
      throw err;
    }
    return payload === null ? { ok:true, text:text } : payload;
  }

  function truncate(value, limit){
    var text = String(value == null ? "" : value);
    return text.length > limit ? text.slice(0, limit) : text;
  }

  function real(){
    return {
      version: VIEW_VERSION,
      app: app,
      __hostContext: (function(){ try { return app.getHostContext() || null; } catch(e){ return null; } })(),

      callTool: async function(name, args){
        return parseToolResult(await app.callServerTool({ name:String(name), arguments:args || {} }));
      },

      /* 敲门（ui/message）：文本 only、≤4000、**需用户在宿主聊天面板点确认**，可被忽略。
         忽略不算错误 —— 静默吞掉 reject 并如实回报投递情况（设计 §5.5 纪律 4）。 */
      notifyAgent: async function(text){
        try {
          var result = await app.sendMessage({ role:"user", content:[{ type:"text", text:truncate(text, 4000) }] });
          return { delivered:true, result:result || null };
        } catch(e){
          return { delivered:false, reason:String((e && e.message) || e) };
        }
      },

      /* 便条（ui/update-model-context）：文本 only、≤8000、覆盖式、在 startStream 内一次性消费 */
      setModelContext: async function(text, structured){
        try {
          var params = { content:[{ type:"text", text:truncate(text, 8000) }] };
          if (structured) params.structuredContent = structured;
          await app.updateModelContext(params);
          return { ok:true };
        } catch(e){
          return { ok:false, reason:String((e && e.message) || e) };
        }
      },

      /* 下载（ui/download-file）：宿主只接受 embedded 内容、≤20MB、多条只取第一条。
         base64 由调用方先在本地量好体积再决定要不要走这条路（设计 §5.9）。 */
      downloadFile: async function(name, mime, base64){
        return app.downloadFile({ contents:[{ type:"resource", resource:{
          uri: "pptx-html://export/" + encodeURIComponent(String(name)),
          mimeType: mime || "application/octet-stream",
          blob: String(base64 || "")
        }}]});
      },

      openLink: async function(url){
        return app.openLink({ url: String(url) });
      },

      log: function(level, message){
        try { app.sendLog({ level: level || "info", data: truncate(message, 2000) }); } catch(e){}
      },

      /* 宿主 size-changed 只跟随高度（宽度不动）、钳制到 maxHeight。
         允许调用方给**期望高度**（工作台要"宿主编制内的最高"时用
         hostContext.containerDimensions.maxHeight）；不传就报文档自身高度，旧语义不变。 */
      reportSize: function(height, width){
        try {
          var h = (typeof height === "number" && isFinite(height) && height > 0)
                    ? height : document.documentElement.scrollHeight;
          var w = (typeof width === "number" && isFinite(width) && width > 0)
                    ? width : document.documentElement.clientWidth;
          app.sendSizeChanged({ width: Math.round(w), height: Math.round(h) });
        } catch(e){}
      },

      hostContext: function(){ try { return app.getHostContext() || null; } catch(e){ return null; } },
      hostCapabilities: function(){ try { return app.getHostCapabilities() || null; } catch(e){ return null; } },
      /* 注册期可能早于 SDK 加载：统一存到 api 上，由 connect 前装好的包装函数转发。
         不要在这里重新赋值 app.onteardown —— 握手完成后注册一次性事件会被 SDK 抛错。 */
      onTeardown: function(cb){ api.__teardown = cb; },
      /* 注册即重放缓冲（载荷可能早于注册到达）——与引导期同名函数行为保持一致 */
      onToolInput: function(cb){ api.__toolInput = cb;
        if (api.__lastToolInput){ try { cb(api.__lastToolInput); } catch(e){} } },
      onToolResult: function(cb){ api.__toolResult = cb;
        if (api.__lastToolResult){ try { cb(api.__lastToolResult); } catch(e){} } }
    };
  }

  function install(real_api){
    Object.keys(real_api).forEach(function(key){ api[key] = real_api[key]; });
    api.__pending = false;
    api.__app = app;
  }

  (async function(){
    try {
      await app.connect(new PostMessageTransport());
      install(real());
      if (api.__resolveReady) api.__resolveReady(api.__hostContext);
    } catch(e){
      if (api.__rejectReady) api.__rejectReady(e);
    }
  })();
})();
