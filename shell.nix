{ pkgs ? import <nixpkgs> {}, full }:

let
  pythonPkgs = python-packages: with python-packages; [
    virtualenv
  ];
  pythonEnv = pkgs.python3.withPackages pythonPkgs;
  lib-path = with pkgs; lib.makeLibraryPath [
    libffi
    openssl
    stdenv.cc.cc
  ];
in
  pkgs.mkShell {
    buildInputs = with pkgs; [
      pythonEnv
      jo
      jq
    ];
    shellHook = ''
      export "LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$NIX_LD_LIBRARY_PATH"
      VENV=.venv
      if test ! -d $VENV; then
        python -m venv $VENV
      fi
      source ./$VENV/bin/activate
      pip install -r requirements.txt
      pip install -r requirements.dev.txt
    '' + (if full then ''
      pip install -r requirements.bark.txt
      python -c "import nltk; nltk.download('punkt')"
    '' else '''') + ''
      pip install -e .
      yes | mypy --install-types
      zsh
    '';
  }
