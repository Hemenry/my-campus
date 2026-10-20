Component({
  options: { styleIsolation: 'apply-shared' },
  properties: {
    rows: { type: Number, value: 3 }
  },
  data: {
    lines: [0, 1, 2]
  },
  observers: {
    rows(value) {
      const count = Math.max(1, Math.min(6, Number(value) || 3));
      this.setData({ lines: Array.from({ length: count }, (item, index) => index) });
    }
  }
});
