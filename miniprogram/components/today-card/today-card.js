Component({
  options: { styleIsolation: 'apply-shared' },
  properties: {
    pending: { type: Number, value: 0 },
    streak: { type: Number, value: 0 },
    finished: { type: Boolean, value: false }
  },
  methods: {
    onStart() {
      this.triggerEvent('start');
    }
  }
});
