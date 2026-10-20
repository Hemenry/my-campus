Component({
  properties: {
    placeholder: { type: String, value: '' },
    value: { type: String, value: '' },
    readonly: { type: Boolean, value: true }
  },
  methods: {
    onTap() {
      if (this.data.readonly) this.triggerEvent('tap');
    },
    onInput(e) {
      this.triggerEvent('input', { value: e.detail.value });
    },
    onConfirm(e) {
      this.triggerEvent('confirm', { value: e.detail.value });
    },
    onClear() {
      this.triggerEvent('input', { value: '' });
      this.triggerEvent('clear');
    }
  }
});
