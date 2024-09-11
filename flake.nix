{
  description = "Lightweight endpoints for serving owt yer like";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils, ... }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { system = system; config.allowUnfree = true; };
      in with pkgs;
        let
          args = {
            pkgs = pkgs;
            doCheck = false;
            onWSL = false;
            useCUDA = false;
            useROCm = false;
            enableBark = false;
            enableParler = false;
            enableMeloTTS = false;
          };
        in {
          devShells = rec {
            default = callPackage ./shell.nix args;
            CUDA = callPackage ./shell.nix (args // { useCUDA = true; });
            WSL-CUDA-MeloTTS = callPackage ./shell.nix (args // { onWSL = true; useCUDA = true; enableMeloTTS = true; });
            ROCm = callPackage ./shell.nix (args // { useROCm = true; });
            ROCm-MeloTTS = callPackage ./shell.nix (args // { useROCm = true; enableMeloTTS = true; });
            wsl = callPackage ./shell.nix (args // { useCUDA = true; onWSL = true;});
            MeloTTS = callPackage ./shell.nix (args // { enableMeloTTS = true; });
          };
          overlays = [
            (final: prev: {
              python3 = prev.python3.override {
                packageOverrides = self: super: super // { owt = final.owt-lib; };
              };
              python3Packages = final.python3.pkgs;
            })
          ];
          packages = rec {
            owt-lib = callPackage ./default.nix { };
            owt = python3Packages.toPythonApplication owt-lib;
            default = owt;
          };
        });
}
