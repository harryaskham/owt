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
            acceleration = null;
            enableBark = false;
            enableParler = false;
            enableMeloTTS = false;
            enableMoshi = false;
            legacyCUDA = false;
          };
        in {
          devShells = rec {
            default = callPackage ./shell.nix args;
            bark-cpu = callPackage ./shell.nix (args // { acceleration = "cpu"; enableBark = true; });
            # TODO: Autogenerate the below (pure flakes don't take arguments, need to run this across many different machines)
            CUDA = callPackage ./shell.nix (args // { acceleration = "cuda"; });
            CUDA-MeloTTS = callPackage ./shell.nix (args // { acceleration = "cuda"; enableMeloTTS = true; });
            CUDA-bark = callPackage ./shell.nix (args // { acceleration = "cuda"; enableBark = true; });
            WSL-CUDA-bark = callPackage ./shell.nix (args // { acceleration = "cuda"; enableBark = true; onWSL = true; });
            CUDA-legacy-MeloTTS = callPackage ./shell.nix (args // { acceleration = "cuda"; enableMeloTTS = true; legacyCUDA = true; });
            CUDA-legacy-bark = callPackage ./shell.nix (args // { acceleration = "cuda"; enableBark = true; legacyCUDA = true; });
            WSL-CUDA-MeloTTS = callPackage ./shell.nix (args // { onWSL = true; acceleration = "cuda"; enableMeloTTS = true; });
            ROCm = callPackage ./shell.nix (args // { acceleration = "rocm"; });
            ROCm-bark = callPackage ./shell.nix (args // { acceleration = "rocm"; enableBark = true; });
            ROCm-MeloTTS = callPackage ./shell.nix (args // { acceleration = "rocm"; enableMeloTTS = true; });
            ROCm-parler = callPackage ./shell.nix (args // { acceleration = "rocm"; enableParler = true; });
            ROCm-moshi = callPackage ./shell.nix (args // { acceleration = "rocm"; enableMoshi = true; });
            wsl = callPackage ./shell.nix (args // { acceleration = "cuda"; onWSL = true;});
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
