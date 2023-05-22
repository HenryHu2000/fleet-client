mkdir optee
cd optee
repo init -u https://github.com/OP-TEE/manifest.git -m hikey960.xml -b 3.18.0
repo sync -j4 --no-clone-bundle
cd build
make -j2 toolchains
make -j `nproc`
