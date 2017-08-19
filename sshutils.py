import os

from eventlet import pools
import paramiko
import six

class SSHPool(pools.Pool):
    """A simple eventlet pool to hold ssh connections."""

    def __init__(self, ip, port, conn_timeout, login, password=None,
                 privatekey=None, *args, **kwargs):
        self.ip = ip
        self.port = port
        self.login = login
        self.password = password
        self.conn_timeout = conn_timeout if conn_timeout else None
        self.privatekey = privatekey
        self.hosts_key_file = None

        # Validate good config setting here.
        # Paramiko handles the case where the file is inaccessible.
        if not CONF.ssh_hosts_key_file:
            raise exception.ParameterNotFound(param='ssh_hosts_key_file')
        elif not os.path.isfile(CONF.ssh_hosts_key_file):
            # If using the default path, just create the file.
            if CONF.state_path in CONF.ssh_hosts_key_file:
                open(CONF.ssh_hosts_key_file, 'a').close()
            else:
                msg = (_("Unable to find ssh_hosts_key_file: %s") %
                       CONF.ssh_hosts_key_file)
                raise exception.InvalidInput(reason=msg)

        if 'hosts_key_file' in kwargs.keys():
            self.hosts_key_file = kwargs.pop('hosts_key_file')
            LOG.info("Secondary ssh hosts key file %(kwargs)s will be "
                     "loaded along with %(conf)s from /etc/cinder.conf.",
                     {'kwargs': self.hosts_key_file,
                      'conf': CONF.ssh_hosts_key_file})

        LOG.debug("Setting strict_ssh_host_key_policy to '%(policy)s' "
                  "using ssh_hosts_key_file '%(key_file)s'.",
                  {'policy': CONF.strict_ssh_host_key_policy,
                   'key_file': CONF.ssh_hosts_key_file})

        self.strict_ssh_host_key_policy = CONF.strict_ssh_host_key_policy

        if not self.hosts_key_file:
            self.hosts_key_file = CONF.ssh_hosts_key_file
        else:
            self.hosts_key_file += ',' + CONF.ssh_hosts_key_file

        super(SSHPool, self).__init__(*args, **kwargs)

    def create(self):
        try:
            ssh = paramiko.SSHClient()
            if ',' in self.hosts_key_file:
                files = self.hosts_key_file.split(',')
                for f in files:
                    ssh.load_host_keys(f)
            else:
                ssh.load_host_keys(self.hosts_key_file)
            # If strict_ssh_host_key_policy is set we want to reject, by
            # default if there is not entry in the known_hosts file.
            # Otherwise we use AutoAddPolicy which accepts on the first
            # Connect but fails if the keys change.  load_host_keys can
            # handle hashed known_host entries.
            if self.strict_ssh_host_key_policy:
                ssh.set_missing_host_key_policy(paramiko.RejectPolicy())
            else:
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            if self.password:
                ssh.connect(self.ip,
                            port=self.port,
                            username=self.login,
                            password=self.password,
                            timeout=self.conn_timeout)
            elif self.privatekey:
                pkfile = os.path.expanduser(self.privatekey)
                privatekey = paramiko.RSAKey.from_private_key_file(pkfile)
                ssh.connect(self.ip,
                            port=self.port,
                            username=self.login,
                            pkey=privatekey,
                            timeout=self.conn_timeout)
            else:
                msg = _("Specify a password or private_key")
                raise exception.CinderException(msg)

            # Paramiko by default sets the socket timeout to 0.1 seconds,
            # ignoring what we set through the sshclient. This doesn't help for
            # keeping long lived connections. Hence we have to bypass it, by
            # overriding it after the transport is initialized. We are setting
            # the sockettimeout to None and setting a keepalive packet so that,
            # the server will keep the connection open. All that does is send
            # a keepalive packet every ssh_conn_timeout seconds.
            if self.conn_timeout:
                transport = ssh.get_transport()
                transport.sock.settimeout(None)
                transport.set_keepalive(self.conn_timeout)
            return ssh
        except Exception as e:
            msg = _("Error connecting via ssh: %s") % six.text_type(e)
            LOG.error(msg)
            raise paramiko.SSHException(msg)

    def get(self):
        """Return an item from the pool, when one is available.
        This may cause the calling greenthread to block. Check if a
        connection is active before returning it.
        For dead connections create and return a new connection.
        """
        conn = super(SSHPool, self).get()
        if conn:
            if conn.get_transport().is_active():
                return conn
            else:
                conn.close()
        try:
            new_conn = self.create()
        except Exception:
            LOG.error("Create new item in SSHPool failed.")
            with excutils.save_and_reraise_exception():
                if conn:
                    self.current_size -= 1
        return new_conn

    def remove(self, ssh):
        """Close an ssh client and remove it from free_items."""
        ssh.close()
        if ssh in self.free_items:
            self.free_items.remove(ssh)
            if self.current_size > 0:
                self.current_size -= 1