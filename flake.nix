{
  description = "Stock options project dev shell";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs }:
    let
      system = "x86_64-linux";
      pkgs = import nixpkgs {
        inherit system;
        config.allowUnfree = true;
      };
    in {
      devShells.${system}.default = pkgs.mkShell {
        packages = with pkgs; [
          python311
          python311Packages.pip
          python311Packages.virtualenv
          python311Packages.setuptools
          python311Packages.wheel

          uv

          docker
          docker-compose

          postgresql_15
          redis
          gcc
          gnumake
          pkg-config
          openssl
          libffi
          zlib

          git
          curl
          jq
        ];

        shellHook = ''
          export PYTHONPATH="$PWD"
          export ENVIRONMENT=dev
          export DATABASE_URL="postgresql://options_user:options_password@localhost:5432/options_tracker"
          export REDIS_URL="redis://localhost:6379/0"

          echo "Stock options dev shell"
          echo "Python: $(python --version)"
          echo ""
          echo "Next:"
          echo "  python -m venv .venv"
          echo "  source .venv/bin/activate"
          echo "  pip install -r requirements.txt"
          echo "  docker compose up -d postgres redis app"
        '';
      };
    };
}
