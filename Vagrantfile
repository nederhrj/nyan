# Vagrantfile
VAGRANTFILE_API_VERSION = "2"

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|

    config.vm.provision "shell", inline: "echo 'Starting Nyan Vagrant Test Environment'"
    config.vm.box = "Centos 6.4 x32"
    config.vm.box_url = "http://developer.nrel.gov/downloads/vagrant-boxes/CentOS-6.4-i386-v20130731.box"

    # nyan
    config.vm.define "nyan" do |nyan|

      nyan.vm.provider :virtualbox do |vb|
      #  vb.customize ["modifyvm", :id, "--memory", "1024", "--name", "ansible-plaything"]
        vb.name = "nyan"
        vb.gui = true
      end

      nyan.vm.provision "ansible" do |ansible|
        ansible.playbook = "provisioning/playbook.yml"
        ansible.verbose = true
      end

      nyan.vm.network :forwarded_port, guest: 5000, host: 5001
      nyan.vm.network :forwarded_port, guest: 27017, host: 27018
      nyan.vm.network :forwarded_port, guest: 61613, host: 61614
      #nyan.vm.network :private_network, ip: "192.168.33.10"
      # config.vm.network :private_network, ip: "192.168.33.10"
      # config.vm.network :public_network

      # config.ssh.forward_agent = true

      # Share an additional folder to the guest VM. The first argument is
      # the path on the host to the actual folder. The second argument is
      # the path on the guest to mount the folder. And the optional third
      # argument is a set of non-required options.
      nyan.vm.synced_folder "./data", "/vagrant_data"
    end
end