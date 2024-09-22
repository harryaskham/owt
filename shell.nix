{ pkgs ? import <nixpkgs> {}, doCheck, onWSL, acceleration, legacyCUDA, enableBark, enableParler, enableMeloTTS, enableMoshi }:

with pkgs.lib;

let
  pythonPkgs = (ps: with ps; [
    virtualenv
  ]);
  pythonEnv = pkgs.python3.withPackages pythonPkgs;
  cudaLibs = with pkgs; [
    cudaPackages.cudatoolkit
    linuxPackages.nvidia_x11
    stdenv.cc.cc
    stdenv.cc.cc.lib
  ];
  useCUDA = acceleration == "cuda";
  useROCm = acceleration == "rocm";
  useCPU = acceleration == "cpu";
  venv = if useCUDA then ".venv-cuda" else if useROCm then ".venv-rocm" else if useCPU then ".venv-cpu" else ".venv";
in pkgs.mkShell (
  (optionalAttrs (enableMoshi && !onWSL) {
    NIX_LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath [ pkgs.portaudio ];
    NIX_LD = with pkgs; lib.fileContents "${stdenv.cc}/nix-support/dynamic-linker";
  }) // (
  optionalAttrs (useCUDA && !onWSL) {
    NIX_LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath cudaLibs;
    NIX_LD = with pkgs; lib.fileContents "${stdenv.cc}/nix-support/dynamic-linker";
  }) // {
    doCheck = doCheck;
    buildInputs = with pkgs; ([
      pythonEnv
      pkg-config
      jo
      jq
      libffi
      openssl
      stdenv.cc.cc
      stdenv.cc.cc.lib
      gcc.cc
      zlib
      zlib.dev
    ] ++ (optionals useCUDA cudaLibs)
    ++ (optionals enableMeloTTS [rustc cargo mecab])
    ++ (optionals enableBark [ffmpeg])
    ++ (optionals enableMoshi [rustc cargo portaudio])
    );
    shellHook = ''
      export LD_LIBRARY_PATH="$LD_LIBRARY_PATH:$NIX_LD_LIBRARY_PATH:~/.nix-profile/lib"

      VENV=${venv}
      if test ! -d $VENV; then
        python -m venv $VENV
      fi
        source ./$VENV/bin/activate
      '' + optionalString useROCm ''
        pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/rocm6.1
        export HIP_VISIBLE_DEVICES=0,1
        export HCC_AMDGPU_TARGET=gfx1100
        export HSA_OVERRIDE_GFX_VERSION=11.0.0
      '' + optionalString useCPU ''
        pip install torch torchvision torchaudio
      '' + ''
        pip install -r requirements.txt
        pip install -r requirements.dev.txt
      '' + optionalString useCUDA ''

        ${if legacyCUDA # TITAN GTX
        then ''pip install torch==2.2.0+cu121 torchvision==0.17.0+cu121 torchaudio==2.2.0+cu121 -f https://download.pytorch.org/whl/torch_stable.html''
        else ''pip install torch torchvision torchaudio''}

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
        pip install -r requirements.tts.txt
        pip install -r requirements.bark.txt
      '' + optionalString enableParler ''
        pip install -r requirements.tts.txt
        pip install -r requirements.parler.txt
        TORCH_LOGS="+dynamo"
        TORCHDYNAMO_VERBOSE=1
      '' + optionalString enableMoshi ''
        pip install -r requirements.tts.txt
        pip install -r requirements.moshi.txt
      '' + optionalString (enableParler && useCUDA) ''
        # Flash attention compilation seems to require CUDA
        pip install flash-attn --no-build-isolation
        # Without this, Triton tries nonexistent /sbin/ldconfig next
        export TRITON_LIBCUDA_PATH="$CUDA_PATH"
        export TRITON_LIBCUDART_PATH="$(pwd)/lib/python3.12/site-packages/nvidia/cuda_runtime/lib"
      '' + optionalString enableMeloTTS ''
        export RUSTFLAGS="-A invalid_reference_casting"  # needed for melotts+tokenizers
        pip install -r requirements.tts.txt
        pip install -r requirements.melotts.txt
        if [[ ! -d ./$VENV/lib/python3.12/site-packages/unidic/dicdir ]]; then
          python -m unidic download
        fi
        python -c "import nltk; nltk.download('averaged_perceptron_tagger_eng')"
      '' + ''
        pip install -e .
        yes | mypy --install-types
      '';
  })
