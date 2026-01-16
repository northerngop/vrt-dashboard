do:
	./vrt.py
	cat vrt.csv
	cat vrt.md
	cat vrt.txt

push:
	GIT_SSH_COMMAND="ssh -i ~/.ssh/id_ed25519" git push
