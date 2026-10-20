Component({
  options: { styleIsolation: 'apply-shared' },
  properties: {
    post: { type: Object, value: {} }
  },
  methods: {
    onTap() {
      this.triggerEvent('tap', { id: this.data.post.id });
    },
    onLike() {
      this.triggerEvent('like', { id: this.data.post.id });
    },
    onCollect() {
      this.triggerEvent('collect', { id: this.data.post.id });
    }
  }
});
