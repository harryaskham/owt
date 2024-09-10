{ pkgs ? import <nixpkgs> {}, doCheck, onWSL, useCUDA, useROCm, enableBark, enableParler, enableMeloTTS }:

with pkgs.lib;

let
  pythonPkgs = (ps: with ps; [
    virtualenv
  ]);
  pythonEnv = pkgs.python3.withPackages pythonPkgs;
  cudaLibs = with pkgs; [
    cudaPackages.cudatoolkit
    linuxPackages.nvidia_x11
  ];
in pkgs.mkShell (
  optionalAttrs useCUDA {
    NIX_LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath cudaLibs;
    NIX_LD = with pkgs; lib.fileContents "${stdenv.cc}/nix-support/dynamic-linker";
  } // {
    doCheck = doCheck;
    buildInputs = with pkgs; ([
      pythonEnv
      pkg-config
      jo
      jq
      libffi
      openssl
      stdenv.cc.cc
      gcc.cc
      zlib
      zlib.dev
    ] ++ (optionals useCUDA cudaLibs)
    ++ (optionals enableMeloTTS [rustc cargo mecab]));
    shellHook = ''
      export LD_LIBRARY_PATH="$LD_LIBRARY_PATH:$NIX_LD_LIBRARY_PATH"

      VENV=.venv
      if test ! -d $VENV; then
        python -m venv $VENV
      fi
      source ./$VENV/bin/activate
    '' + optionalString useROCm ''
      pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/rocm6.1
      export HIP_VISIBLE_DEVICES=0
      export HSA_OVERRIDE_GFX_VERSION=11.0.0
    '' + ''
      pip install -r requirements.txt
      pip install -r requirements.dev.txt
    '' + optionalString useCUDA ''
      export LD_LIBRARY_PATH="$LD_LIBRARY_PATH:$NIX_LD_LIBRARY_PATH"
      export LD_LIBRARY_PATH="$LD_LIBRARY_PATH:$CUDA_PATH"
      export LD_LIBRARY_PATH="$LD_LIBRARY_PATH:/run/opengl-driver/lib"
      export LD_LIBRARY_PATH="$LD_LIBRARY_PATH:${pkgs.linuxPackages.nvidia_x11}/lib"
      export LD_LIBRARY_PATH="$LD_LIBRARY_PATH:${pkgs.ncurses5}/lib"
      export EXTRA_LDFLAGS="-L/lib -L${pkgs.linuxPackages.nvidia_x11}/lib"
      export EXTRA_CCFLAGS="-I/usr/include"
    '' + optionalString onWSL ''
      export LD_LIBRARY_PATH="$LD_LIBRARY_PATH:/run/opengl-driver/lib"
    '' + optionalString (enableBark || enableParler) ''
      python -c "import nltk; nltk.download('punkt'); nltk.download('punkt_tab')"
    '' + optionalString enableBark ''
      pip install -r requirements.bark.txt
    '' + optionalString enableParler ''
      pip install -r requirements.parler.txt
      TORCH_LOGS="+dynamo"
      TORCHDYNAMO_VERBOSE=1
    '' + optionalString (enableParler && useCUDA) ''
      # Flash attention compilation seems to require CUDA
      pip install flash-attn --no-build-isolation
      # Without this, Triton tries nonexistent /sbin/ldconfig next
      export TRITON_LIBCUDA_PATH="$CUDA_PATH"
      export TRITON_LIBCUDART_PATH="$(pwd)/lib/python3.12/site-packages/nvidia/cuda_runtime/lib"
    '' + optionalString enableMeloTTS ''
      export RUSTFLAGS="-A invalid_reference_casting"  # needed for melotts+tokenizers
      pip install -r requirements.melotts.txt
      if [[ ! -d .venv/lib/python3.12/site-packages/unidic/dicdir ]]; then
        python -m unidic download
      fi
      python -c "import nltk; nltk.download('averaged_perceptron_tagger_eng')"
    '' + ''
      pip install -e .
      yes | mypy --install-types
      zsh
    '';
  })
