Component({
  properties: {
    items: { type: Array, value: [] },
    active: { type: Number, value: 0 }
  },
  methods: {
    onChange(e) {
      const index = Number(e.currentTarget.dataset.index);
      if (index === this.data.active) return;
      this.triggerEvent('change', { index });
    }
  }
});
