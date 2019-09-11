# droplet-docker-jupyter

This is a simple script that allowed me to create 'disposable' DigitalOcean droplets whenever I came across a juicy dataset I wanted to tackle.

My workflow was:

1. Clone this repo
2. Create a `virtualenv` inside it.
3. Install dependencies listed inside *requirements.txt* with `pip`
4. Activate the virtual environment
5. `python ./manage_droplet.py --cloud-config ./droplet-con-docker.yaml`
6. If there were no errors, copy the droplet_id
7. `python ./manage_droplet.py --check-ip droplet_id`
8. This should have returned the newly created droplet IP. Username and password are defined inside *droplet-con-docker.yaml*
9. `ssh` to the droplet, run jupyter and then use it's web interface.

