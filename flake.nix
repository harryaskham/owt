{
  description = "Lightweight endpoints for serving owt yer like";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils, ... }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
      in with pkgs; {
        devShells = {
          default = callPackage ./shell.nix { inherit pkgs; full = true; };
          core = callPackage ./shell.nix { inherit pkgs; full = false; };
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
