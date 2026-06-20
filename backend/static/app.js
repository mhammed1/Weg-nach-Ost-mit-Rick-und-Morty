const { createApp, nextTick } = Vue;

createApp({
  data() {
    return {
      draft: "",
      loadingChat: false,
      loadingIngest: false,
      messages: JSON.parse(localStorage.getItem("oracle_messages") || "[]"),
    };
  },
  methods: {
    async runIngest() {
      this.loadingIngest = true;
      try {
        const res = await fetch("/api/ingest", { method: "POST" });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Ingest fehlgeschlagen");
      } catch (e) {
        alert(String(e.message || e));
      } finally {
        this.loadingIngest = false;
      }
    },
    persistMessages() {
      localStorage.setItem("oracle_messages", JSON.stringify(this.messages.slice(-50)));
    },
    clearHistory() {
      this.messages = [];
      localStorage.removeItem("oracle_messages");
    },
    async sendMessage() {
      const question = this.draft.trim();
      if (!question) return;

      this.messages.push({ role: "user", content: question });
      this.draft = "";
      this.loadingChat = true;
      this.persistMessages();

      try {
        const history = this.messages.map((m) => ({ role: m.role, content: m.content }));
        const res = await fetch("/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: question, history }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Chat fehlgeschlagen");

        this.messages.push({
          role: "assistant",
          content: data.answer,
          sources: data.sources || [],
          confidence: data.confidence,
        });
        this.persistMessages();
        await nextTick();
        this.$refs.chatWindow.scrollTop = this.$refs.chatWindow.scrollHeight;
      } catch (e) {
        alert(String(e.message || e));
      } finally {
        this.loadingChat = false;
      }
    },
  },
}).mount("#app");
