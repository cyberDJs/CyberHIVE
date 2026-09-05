# Run the one-time local provisioning wizard only on the physical tty1 login.
case $- in *i*) ;; *) return ;; esac
if [ -t 0 ] && [ "$(tty 2>/dev/null || true)" = '/dev/tty1' ]; then
  if [ ! -e /var/lib/cyberhive-persist/state/provisioned ]; then
    sudo -n /usr/local/sbin/cyberhive-firstboot || true
  fi
fi
