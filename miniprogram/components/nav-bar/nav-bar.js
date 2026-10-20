Component({
  options: { multipleSlots: true },
  properties: {
    brandName: { type: String, value: 'GeekCampus' },
    school: { type: String, value: '星河大学' },
    unread: { type: Number, value: 0 },
    statusBarHeight: { type: Number, value: 20 },
    showPublish: { type: Boolean, value: false }
  },
  methods: {
    onNotify() {
      this.triggerEvent('tap-notify');
    },
    onSchool() {
      this.triggerEvent('tap-school');
    },
    onPublish() {
      this.triggerEvent('tap-publish');
    }
  }
});
