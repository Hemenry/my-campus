Component({
  properties: {
    items: { type: Array, value: [] }
  },
  methods: {
    onSelect(e) {
      const key = e.currentTarget.dataset.key;
      this.triggerEvent('select', { key });
    }
  }
});
