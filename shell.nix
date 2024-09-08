{ pkgs ? import <nixpkgs> {}, full }:

let
  pythonPkgs = python-packages: with python-packages; [
    virtualenv
  ];
  pythonEnv = pkgs.python3.withPackages pythonPkgs;
  libs = with pkgs; [
    libffi
    openssl
    stdenv.cc.cc
    glibc
    glibc.dev
    gcc.cc
    zlib
    zlib.dev
    cudaPackages.cudatoolkit
    linuxPackages.nvidia_x11
  ];
in
  pkgs.mkShell {
    NIX_LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath libs;
    NIX_LD = with pkgs; lib.fileContents "${stdenv.cc}/nix-support/dynamic-linker";
    doCheck = false;
    buildInputs = with pkgs; [
      pythonEnv
      jo
      jq
    ] ++ libs;
    shellHook = ''
      export LD_LIBRARY_PATH="$LD_LIBRARY_PATH:$NIX_LD_LIBRARY_PATH"
      export LD_LIBRARY_PATH="$LD_LIBRARY_PATH:$CUDA_PATH"
      export LD_LIBRARY_PATH="$LD_LIBRARY_PATH:/run/opengl-driver/lib"
      export LD_LIBRARY_PATH="$LD_LIBRARY_PATH:${pkgs.linuxPackages.nvidia_x11}/lib"
      export LD_LIBRARY_PATH="$LD_LIBRARY_PATH:${pkgs.ncurses5}/lib"
      export EXTRA_LDFLAGS="-L/lib -L${pkgs.linuxPackages.nvidia_x11}/lib"
      export EXTRA_CCFLAGS="-I/usr/include"

      VENV=.venv
      if test ! -d $VENV; then
        python -m venv $VENV
      fi
      source ./$VENV/bin/activate

      pip install -r requirements.txt
      pip install -r requirements.dev.txt

    '' + (if full then ''
      # Bark
      pip install -r requirements.bark.txt

      # Parler
      pip install -r requirements.parler.txt
      # Without this, Triton tries nonexistent /sbin/ldconfig next
      export TRITON_LIBCUDA_PATH="$CUDA_PATH"
      export TRITON_LIBCUDART_PATH="$(pwd)/lib/python3.12/site-packages/nvidia/cuda_runtime/lib"
      TORCH_LOGS="+dynamo"
      TORCHDYNAMO_VERBOSE=1

      python -c "import nltk; nltk.download('punkt')"
      pip install flash-attn --no-build-isolation
    '' else '''') + ''
      pip install -e .
      yes | mypy --install-types
      zsh
    '';
  }
