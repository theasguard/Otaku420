        for i in torrent_list:  # Loop through individual torrents
            if control.real_debrid_enabled():
                self.threads.append(threading.Thread(target=self.real_debrid_worker, args=([i],)))  # Pass single torrent list

            if control.debrid_link_enabled():
                self.threads.append(threading.Thread(target=self.debrid_link_worker, args=([i],)))

            if control.premiumize_enabled():
                self.threads.append(threading.Thread(target=self.premiumize_worker, args=([i],)))

            if control.all_debrid_enabled():
                self.threads.append(threading.Thread(target=self.all_debrid_worker, args=([i],)))
